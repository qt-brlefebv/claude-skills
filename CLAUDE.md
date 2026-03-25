# find-msvc

This project provides the `/msvc` skill (aliases: `/vcvars`, `/find-msvc`) for Claude Code on Windows. It discovers MSVC/Visual Studio installations and activates their developer environment for build commands.

## MSVC Environment Integration

When `.msvc_env.sh` exists in the project root, **always source it before running build-related commands**:

```bash
source .msvc_env.sh && cmake ...
source .msvc_env.sh && cl /EHsc main.cpp
source .msvc_env.sh && ninja
```

This applies to: `cmake`, `cl`, `cl.exe`, `nmake`, `msbuild`, `link`, `link.exe`, `ninja`, `lib`, `lib.exe`, `rc`, `rc.exe`, `dumpbin`, `ml`, `ml64`, and any other MSVC toolchain command.

If `.msvc_env.sh` does not exist, do not attempt to source it — suggest running `/msvc` first.
