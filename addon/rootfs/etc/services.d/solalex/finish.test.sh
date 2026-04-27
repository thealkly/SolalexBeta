#!/usr/bin/env bash
# Manual smoketest for the s6 finish handler (Story 3.9).
# Run: bash addon/rootfs/etc/services.d/solalex/finish.test.sh
# NOT wired into CI — bashio is unavailable outside the addon image.
set -u

# Bash >= 4.0 is required: the stub function names below contain ``::``
# which Bash 3.2 (default on macOS) rejects with "not a valid identifier".
# On macOS install via ``brew install bash`` and run with /opt/homebrew/bin/bash.
if (( BASH_VERSINFO[0] < 4 )); then
    echo "ERROR: this smoketest needs bash >= 4.0 (current: ${BASH_VERSION:-unknown})." >&2
    echo "       On macOS: 'brew install bash' and run with /opt/homebrew/bin/bash." >&2
    exit 2
fi

SCRIPT="$(cd "$(dirname "$0")" && pwd)/finish"
FAIL=0

run() {
    local desc="$1"
    local expected="$2"
    shift 2

    # Stub bashio + bashio::log.* as no-ops so the script runs in a plain
    # bash without the HA add-on runtime. The stubs are defined in a
    # wrapper bash invocation so they shadow the real `#!/usr/bin/with-contenv
    # bashio` shebang behaviour during the test.
    local actual
    actual=$(
        bash -c "
            bashio() { :; }
            bashio::log.info() { :; }
            bashio::log.warning() { :; }
            bashio::log.error() { :; }
            export -f bashio
            export -f bashio::log.info bashio::log.warning bashio::log.error
            # Drop the with-contenv shebang by sourcing the body via bash.
            # stdout silenced (we only care about the exit code), stderr
            # left intact so a future regression in finish surfaces as a
            # visible error instead of a silent FAIL with a wrong exit code.
            bash '$SCRIPT' $* >/dev/null
            echo \$?
        " | tail -1
    )

    if [[ "${actual}" == "${expected}" ]]; then
        printf 'PASS  %-32s expected=%s actual=%s\n' "${desc}" "${expected}" "${actual}"
    else
        printf 'FAIL  %-32s expected=%s actual=%s\n' "${desc}" "${expected}" "${actual}"
        FAIL=1
    fi
}

run "exit 0 (clean)"             "0"    0
run "exit 125 (explicit halt)"   "125"  125
run "signal 15 (SIGTERM)"        "0"    256 15
run "signal 2 (SIGINT)"          "0"    256 2
run "signal 9 (SIGKILL)"         "1"    256 9
run "exit 137 (real crash)"      "1"    137
run "exit abc (non-numeric)"     "1"    abc

if [[ "${FAIL}" -eq 0 ]]; then
    echo "All finish-handler cases passed."
else
    echo "Some finish-handler cases FAILED."
fi
exit "${FAIL}"
