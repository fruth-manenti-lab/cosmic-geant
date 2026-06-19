#!/usr/bin/env bash
set -euo pipefail

# Launch full-slab cover32 face-mount ADD_SCAN runs.
# By default this starts a detached screen session if screen is available,
# otherwise it falls back to nohup. Set COVER32_INNER=1 to run foreground.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${BUILD_DIR:-${ROOT}/new_build}"
WORK_DIR="${WORK_DIR:-${BUILD_DIR}/cover32_facemount_work}"
RUN_ROOT="${RUN_ROOT:-${BUILD_DIR}/cover32_facemount_runs}"
SESSION_NAME="${SESSION_NAME:-cover32_muon_scans}"
GEOMETRY_FILE="geometry/faceMountGeometry_1m_cover32_sipms.gdml"
RANDOM_MACRO="macros/cover32_random_muon_1000.mac"
TRAINING_MACRO="macros/cover32_training_muon_10000.mac"

if [[ "${COVER32_INNER:-0}" != "1" ]]; then
    mkdir -p "${RUN_ROOT}"
    launcher_log="${RUN_ROOT}/launcher.log"
    if command -v screen >/dev/null 2>&1; then
        screen -dmS "${SESSION_NAME}" bash -lc "cd '${ROOT}' && COVER32_INNER=1 '${SCRIPT_DIR}/run_cover32_muon_scans.sh' >> '${launcher_log}' 2>&1"
        echo "Started detached screen session: ${SESSION_NAME}"
        echo "Log: ${launcher_log}"
        echo "Attach with: screen -r ${SESSION_NAME}"
    else
        nohup bash -lc "cd '${ROOT}' && COVER32_INNER=1 '${SCRIPT_DIR}/run_cover32_muon_scans.sh'" > "${launcher_log}" 2>&1 &
        echo $! > "${RUN_ROOT}/launcher.pid"
        echo "screen not found; started nohup background job PID $(cat "${RUN_ROOT}/launcher.pid")"
        echo "Log: ${launcher_log}"
    fi
    exit 0
fi

if [[ ! -x "${BUILD_DIR}/sim" ]]; then
    echo "Missing executable: ${BUILD_DIR}/sim" >&2
    echo "Configure/build with ADD_SCAN=ON before running this launcher." >&2
    exit 1
fi

cd "${ROOT}"
GEANT4_ENV="${GEANT4_ENV:-/home/joeyl/geant4/install/bin/geant4.sh}"
if [[ -f "${GEANT4_ENV}" ]]; then
    # Needed for detached nohup/screen runs where .bashrc is not sourced.
    source "${GEANT4_ENV}"
else
    echo "Warning: Geant4 environment script not found: ${GEANT4_ENV}" >&2
fi
python3 analysis/unit_square_32_covering/make_cover32_facemount_gdml.py
python3 analysis/unit_square_32_covering/generate_cover32_scan_macros.py

mkdir -p "${WORK_DIR}/geometry" "${WORK_DIR}/macros" "${WORK_DIR}/output" "${RUN_ROOT}"
cp -a geometry/. "${WORK_DIR}/geometry/"
cp macros/cover32_* "${WORK_DIR}/macros/"
cp analysis/unit_square_32_covering/results/cover32_sipm_mapping_mm.csv "${RUN_ROOT}/"

run_one() {
    local label="$1"
    local macro="$2"
    local outdir="${RUN_ROOT}/${label}"
    mkdir -p "${outdir}"
    rm -f "${WORK_DIR}/output"/MUON-run*_nt_*.csv

    echo "[$(date --iso-8601=seconds)] starting ${label}"
    (
        cd "${WORK_DIR}"
        "${BUILD_DIR}/sim" "${GEOMETRY_FILE}" "${macro}"
    ) > "${outdir}/${label}.log" 2>&1

    cp "${WORK_DIR}/output"/MUON-run*_nt_*.csv "${outdir}/" 2>/dev/null || true
    cp "${WORK_DIR}/${macro}" "${outdir}/"
    case "${label}" in
        random_1000_full_slab)
            cp "${WORK_DIR}/macros/cover32_random_muon_1000_positions.mac" "${outdir}/"
            cp "${WORK_DIR}/macros/cover32_random_muon_1000_positions.csv" "${outdir}/"
            ;;
        training_10000_full_slab)
            cp "${WORK_DIR}/macros/cover32_training_muon_10000_positions.mac" "${outdir}/"
            ;;
    esac
    echo "[$(date --iso-8601=seconds)] finished ${label}; outputs in ${outdir}"
}

run_one "random_1000_full_slab" "${RANDOM_MACRO}"
run_one "training_10000_full_slab" "${TRAINING_MACRO}"

echo "[$(date --iso-8601=seconds)] cover32 runs complete"
