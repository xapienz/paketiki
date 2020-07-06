#!/usr/bin/env python3
import argparse
import json
import os
import re
import shlex
import subprocess

def split_list(list, delimiter):
    part = []
    for line in list:
        if line == delimiter:
            yield part
            part = []
        else:
            part.append(line)
    yield part

def parse_bash_array(str):
    if str is None:
        return None
    elif str.startswith("(") and str.endswith(")"):
        # hiding escaped backslashes to find unescaped quotes
        str = str.replace(r"\\", ":escaped_backslash:")
        pattern = re.compile(r'\[\d+\]="(.*?[^\\])"')
        return list(map(lambda s: s.replace(":escaped_backslash:", r"\\"), pattern.findall(str)))
    else:
        return [str]

# Parse output of bash `set` and return map "key -> value" or "function () -> body"
def parse_set_output(set_output):
    result = {}
    empty_pattern = re.compile(r"^\s*$")
    var_pattern = re.compile(r"^(\w+)=(.*)$")
    fun_title_pattern = re.compile(r"^(\w+ \(\))\s*$")
    fun_begin_pattern = re.compile(r"^{\s*$")
    fun_end_pattern = re.compile(r"^}$")

    fun_name = None
    fun_body = []
    for line in set_output:
        if m := var_pattern.match(line):
            result[m.group(1)] = m.group(2)
        elif m := fun_title_pattern.match(line):
            fun_name = m.group(1)
            fun_body = []
        elif m := fun_end_pattern.match(line):
            result[fun_name] = "\n".join(fun_body)
            fun_name = None
            fun_body = []
        elif m := fun_begin_pattern.match(line):
            continue
        elif fun_name is not None:
            fun_body.append(line)
        elif m := empty_pattern.match(line):
            continue
        else:
            exit("Can't parse line {}, output={}".format(line, '\n'.join(set_output)))

    return result

def read_pkgbuild(file):
    with open(file, "r") as f:
        pkgbuild_contents = f.read()
    separator_before = "PKGBUILD begins here"
    separator_after = "PKGBUILD ends here"
    command = shlex.split("env -i bash")
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pkgbuild = f"""
set
echo {separator_before}
{pkgbuild_contents}
echo {separator_after}
set
    """

    out, err = process.communicate(input=pkgbuild.encode())
    if err:
        exit(f"Bash error: {err.decode()}")
    
    before, rest = split_list(out.decode().split("\n"), separator_before)
    _, after = split_list(rest, separator_after)

    vars_before = parse_set_output(before)
    vars_after = parse_set_output(after)
    
    for key, value in vars_before.items():
        if vars_after[key] == value:
            vars_after.pop(key)

    result = {}
    result["name"] = vars_after.get("pkgname")
    result["version"] = vars_after.get("pkgver")
    result["release"] = vars_after.get("pkgrel")
    result["description"] = vars_after.get("pkgdesc")
    result["source"] = parse_bash_array(vars_after.get("source"))
    result["sha256sums"] = parse_bash_array(vars_after.get("sha256sums"))
    result["md5sums"] = parse_bash_array(vars_after.get("md5sums"))
    result["makedepends"] = parse_bash_array(vars_after.get("makedepends"))
    result["depends"] = parse_bash_array(vars_after.get("depends"))
    result["provides"] = parse_bash_array(vars_after.get("provides"))
    result["replaces"] = parse_bash_array(vars_after.get("replaces"))
    result["conflicts"] = parse_bash_array(vars_after.get("conflicts"))
    result["license"] = parse_bash_array(vars_after.get("license"))
    result["arch"] = parse_bash_array(vars_after.get("arch"))
    result["build()"] = vars_after.get("build ()")
    result["package()"] = vars_after.get("package ()")
    
    return result

def write_json(file, result):
    with open(file, "w") as f:
        print(json.dumps(result, indent=2), file=f)

def write_rpm_section(f, name, value):
    if value:
        print("\n%{}\n{}".format(name, value), file=f)

def write_rpm_array(f, name, array):
    if array:
        for value in array:
            write_rpm_field(f, name, value)

def write_rpm_field(f, name, value):
    if value:
        print("{}: {}".format(name, value), file=f)

def replace_packages(list):
    if not list:
        return []
    with open("pkgbuild_mapping.json", "r") as f:
        mapping = json.load(f)

    result = []
    version_pattern = re.compile(r"^(\w+)=(.*)$")
    for item in list:
        if m := version_pattern.match(item):
            package = m.group(1)
        else:
            package = item

        # TODO: also use version
        if mapped := mapping.get(package):
            result.extend(mapped)
        else:
            result.append(package)
    return result

def wrap_code_section(code):
    if code:
        return '    export pkgdir="%{buildroot}"\n' + code
    else:
        return None

def write_rpm(file, result):
    with open(file, "w") as f:
        write_rpm_field(f, "Name", result.get("name"))
        write_rpm_field(f, "Version", result.get("version"))
        write_rpm_field(f, "Release", result.get("release"))
        write_rpm_field(f, "Summary", result.get("description"))
        write_rpm_array(f, "License", result.get("license"))
        write_rpm_array(f, "Requires", replace_packages(result.get("depends")))
        write_rpm_array(f, "Provides", replace_packages(result.get("provides")))
        write_rpm_array(f, "Conflicts", replace_packages(result.get("conflicts")))
        write_rpm_array(f, "Obsoletes", replace_packages(result.get("replaces")))
        write_rpm_array(f, "BuildRequires", replace_packages(result.get("makedepends")))
        write_rpm_field(f, "Source", "{}-{}.tar.gz".format(result.get("name"), result.get("version")))
        print("%define debug_package %{nil}", file=f)
        write_rpm_section(f, "prep", "%setup")
        write_rpm_section(f, "description", result.get("description"))
        write_rpm_section(f, "build", wrap_code_section(result.get("build()")))
        write_rpm_section(f, "install", wrap_code_section(result.get("package()")))
        write_rpm_section(f, "files", 
            "/*\n" +
            "%exclude %dir /usr/bin\n" +
            "%exclude %dir /usr/lib\n")

def main():
    parser = argparse.ArgumentParser(description="Convert Linux packages")
    parser.add_argument("pkgbuild", help="Path to PKGBUILD file")
    parser.add_argument("output", help="Path to output")
    args = parser.parse_args()
    value = read_pkgbuild(args.pkgbuild)
    write_json(args.output + ".json", value)
    write_rpm(args.output + ".spec", value)

if __name__ == "__main__":
    main()
