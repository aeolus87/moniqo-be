#!/usr/bin/env bash
# Purpose: Provision and launch the Moniqo backend from a clean environment.
# Dependencies: bash, python3 (>=3.10), python3-venv, python3-pip, uvicorn, apt-get (for automatic Python installation on Debian-based systems).
# Usage Examples:
#   bash scripts/bootstrap_backend.sh
#   PORT=9000 ./scripts/bootstrap_backend.sh
# Author Notes: Designed for idempotent use inside WSL/Linux. Automatically installs Python tooling when apt-get is available, creates/updates the virtual environment, installs requirements, and starts the FastAPI server with uvicorn.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="${PROJECT_ROOT}/venv"
PYTHON_BIN="python3"
REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements.txt"
UVICORN_MODULE="app.main:app"
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="${PORT:-8000}"

info() {
  printf "\033[1;34m[INFO]\033[0m %s\n" "$1"
}

warn() {
  printf "\033[1;33m[WARN]\033[0m %s\n" "$1"
}

error() {
  printf "\033[1;31m[ERROR]\033[0m %s\n" "$1" >&2
  exit 1
}

ensure_python() {
  if command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    info "Detected $(command -v "${PYTHON_BIN}") ($(python3 --version 2>/dev/null || echo 'version unknown'))."
    return
  fi

  warn "python3 not found. Attempting installation via apt-get (requires sudo)."

  if ! command -v apt-get >/dev/null 2>&1; then
    error "apt-get is unavailable. Install Python 3 manually and re-run this script."
  fi

  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip

  if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    error "Python installation failed. Install python3 manually and retry."
  fi

  info "python3 successfully installed."
}

ensure_virtualenv() {
  if [ ! -d "${VENV_PATH}" ]; then
    info "Creating virtual environment at ${VENV_PATH}."
    "${PYTHON_BIN}" -m venv "${VENV_PATH}"
  else
    info "Virtual environment already exists at ${VENV_PATH}."
  fi
}

install_requirements() {
  if [ ! -f "${REQUIREMENTS_FILE}" ]; then
    warn "requirements.txt not found at ${REQUIREMENTS_FILE}. Skipping dependency installation."
    return
  fi

  info "Upgrading pip and installing requirements."
  "${VENV_PATH}/bin/python" -m pip install --upgrade pip
  "${VENV_PATH}/bin/python" -m pip install -r "${REQUIREMENTS_FILE}"
}

validate_uvicorn_module() {
  if [ ! -d "${PROJECT_ROOT}/app" ]; then
    error "Expected FastAPI application directory 'app' not found in ${PROJECT_ROOT}."
  fi
}

start_server() {
  local host="${HOST:-${DEFAULT_HOST}}"
  local port="${PORT:-${DEFAULT_PORT}}"

  info "Starting uvicorn server at ${host}:${port} using module ${UVICORN_MODULE}."
  info "Use CTRL+C to stop the server."
  exec "${VENV_PATH}/bin/python" -m uvicorn "${UVICORN_MODULE}" --host "${host}" --port "${port}" --reload
}

main() {
  info "Bootstrapping Moniqo backend environment."
  ensure_python
  ensure_virtualenv
  install_requirements
  validate_uvicorn_module
  start_server
}

main "$@"

