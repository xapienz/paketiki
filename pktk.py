#!/usr/bin/env python3
import argparse
import collections
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

    # platform-specific fields:
    result["pkgbuild_pkgname"] = vars_after.get("_pkgname")
    result["pkgbuild_pkgfolder"] = vars_after.get("_pkgfolder")
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

def write_rpm_variable(f, name, value):
    if value:
        print("%define {} {}".format(name, value), file=f)

def map_packages(mapping, list):
    MappedPackage=collections.namedtuple("MappedPackage", ["packages", "aliases", "extra_deps"])
    if not list:
        return MappedPackage([], [], [])
    
    packages = []
    aliases = []
    extra_deps = []
    version_pattern = re.compile(r"^([\w_-]+)>?<?=(.*)$")
    for item in list:
        if m := version_pattern.match(item):
            package = m.group(1)
        else:
            package = item

        # TODO: also use version
        mapped = mapping.get(package) or {}
        if (mapped_packages := mapped.get("packages")) is None:
            packages.append(package)
        else:
            packages.extend(mapped_packages)
        aliases.extend(mapped.get("aliases") or [])
        extra_deps.extend(mapped.get("extra_deps") or [])
    return MappedPackage(packages, aliases, extra_deps)

def wrap_code_section(code, aliases_list):
    if code:
        vars = """    export pkgdir="%{buildroot}"
    export srcdir="%{srcdir}"
    export pkgname="%{pkgname}"
    export _pkgname="%{_pkgname}"
    export _pkgfolder="%{_pkgfolder}"
"""
        aliases = ""
        for alias in aliases_list:
            aliases += "    alias {}\n".format(alias)
        return vars + aliases + code
    else:
        return None

# append rpm-specific stuff to json
def make_rpm_json(value):
    with open("pkgbuild_mapping.json", "r") as f:
        mapping = json.load(f)

    result = value
    result["rpm_requires"] = map_packages(mapping, result.get("depends")).packages
    result["rpm_provides"] = map_packages(mapping, result.get("provides")).packages
    result["rpm_conflicts"] = map_packages(mapping, result.get("conflicts")).packages
    result["rpm_obsoletes"] = map_packages(mapping, result.get("obsoletes")).packages
    result["rpm_buildrequires"] = map_packages(mapping, result.get("makedepends")).packages
    result["rpm_aliases"] = map_packages(mapping, result.get("makedepends")).aliases
    result["rpm_extra_deps"] = map_packages(mapping, [result.get("name")]).extra_deps
    result["rpm_devel"] = [p + "-devel" for p in result["rpm_requires"] + result["rpm_buildrequires"] + result["rpm_extra_deps"]]
    return result

def write_rpm(file, result):
    with open(file, "w") as f:
        write_rpm_field(f, "Name", result.get("name"))
        write_rpm_field(f, "Version", result.get("version"))
        write_rpm_field(f, "Release", result.get("release"))
        write_rpm_field(f, "Summary", result.get("description"))
        write_rpm_array(f, "License", result.get("license"))
        write_rpm_array(f, "Requires", result.get("rpm_requires"))
        write_rpm_array(f, "Provides", result.get("rpm_provides"))
        write_rpm_array(f, "Conflicts", result.get("rpm_conflicts"))
        write_rpm_array(f, "Obsoletes", result.get("rpm_obsoletes"))
        write_rpm_array(f, "BuildRequires", result.get("rpm_buildrequires"))
        write_rpm_field(f, "Source", "{}-{}.tar.gz".format(result.get("name"), result.get("version")))
        write_rpm_variable(f, "__brp_mangle_shebangs", "%{nil}")
        write_rpm_variable(f, "debug_package", "%{nil}")
        write_rpm_variable(f, "srcdir", "%{_builddir}/" + "{}-{}".format(result.get("name"), result.get("version")))
        # TODO: just write all vars
        write_rpm_variable(f, "pkgname", result.get("name"))
        write_rpm_variable(f, "_pkgname", result.get("pkgbuild_pkgname"))
        write_rpm_variable(f, "_pkgfolder", result.get("pkgbuild_pkgfolder"))
        write_rpm_section(f, "prep", "%setup")
        write_rpm_section(f, "description", result.get("description"))
        write_rpm_section(f, "build", wrap_code_section(result.get("build()"), result.get("rpm_aliases")))
        write_rpm_section(f, "install", wrap_code_section(result.get("package()"), result.get("rpm_aliases")))
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
    value = make_rpm_json(value)
    write_json(args.output + ".json", value)
    write_rpm(args.output + ".spec", value)

if __name__ == "__main__":
    main()
