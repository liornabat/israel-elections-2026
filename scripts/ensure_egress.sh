#!/usr/bin/env bash
# Reach the Central Elections Committee CDN from networks it blocks.
#
# GitHub-hosted runners get CloudFront HTTP 403. A direct request is used
# when it already returns 200. Otherwise this starts a userspace Cloudflare
# WARP SOCKS proxy (no WireGuard kernel module) and exports ALL_PROXY.
# Source this file so the proxy variables stay in the caller. Keys stay in
# a temp directory and are not written to the repo.

ensure_egress() {
  local orig="$PWD"
  local cec_url="https://mapvotes.bechirot.gov.il/data/votes/elections.json"
  local ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
  local bindir="/tmp/election-egress"
  local socks="socks5h://127.0.0.1:40000"
  local code

  probe_direct() {
    env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
      curl -4 -sS -o /dev/null -w '%{http_code}' --max-time 25 \
      -A "$ua" \
      -H "Referer: https://mapvotes.bechirot.gov.il/" \
      "$cec_url" || true
  }

  if [[ "${CEC_FORCE_WARP:-}" != 1 ]]; then
    code=$(probe_direct)
    if [[ "$code" == 200 ]]; then
      echo "committee CDN reachable directly (HTTP 200)"
      return 0
    fi
    echo "committee CDN returned HTTP ${code:-000}; opening a Cloudflare WARP tunnel"
  else
    echo "CEC_FORCE_WARP=1; opening a Cloudflare WARP tunnel"
  fi

  if [[ "$(uname -m)" != "x86_64" ]]; then
    echo "WARP fallback is packaged for x86_64 only (this runner is $(uname -m))"
    return 1
  fi

  mkdir -p "$bindir"
  if [[ ! -x "$bindir/wgcf" ]]; then
    curl -fsSL -o "$bindir/wgcf" \
      "https://github.com/ViRb3/wgcf/releases/download/v2.3.1/wgcf_2.3.1_linux_amd64"
    echo "4fb7a136aa470ece11d17949c7db07b040ec9c604742dc8680bcf1889f85d0c8  $bindir/wgcf" | sha256sum -c -
    chmod +x "$bindir/wgcf"
  fi
  if [[ ! -x "$bindir/wireproxy" ]]; then
    curl -fsSL -o "$bindir/wireproxy.tar.gz" \
      "https://github.com/windtf/wireproxy/releases/download/v1.1.3/wireproxy_linux_amd64.tar.gz"
    echo "e88c1d090740373fc606c1bafd81d9a5eadc642cce5667616e20e9d7a444f51c  $bindir/wireproxy.tar.gz" | sha256sum -c -
    tar -xzf "$bindir/wireproxy.tar.gz" -C "$bindir"
    chmod +x "$bindir/wireproxy"
  fi

  local workdir
  workdir=$(mktemp -d)
  local registered=0
  local attempt
  for attempt in 1 2 3; do
    if (cd "$workdir" && "$bindir/wgcf" register --accept-tos && "$bindir/wgcf" generate); then
      registered=1
      break
    fi
    echo "WARP registration attempt ${attempt} failed"
    sleep 3
  done
  if [[ "$registered" != 1 ]]; then
    echo "Could not register a Cloudflare WARP account from this runner"
    rm -rf "$workdir"
    return 1
  fi

  python3 - "$workdir/wgcf-profile.conf" "$workdir/wireproxy.conf" << 'PY'
import sys
from pathlib import Path
vals = {}
for line in Path(sys.argv[1]).read_text().splitlines():
    if "=" in line and not line.strip().startswith("["):
        key, value = line.split("=", 1)
        vals[key.strip()] = value.strip()
addr = vals["Address"].split(",")[0].strip()
dns = vals["DNS"].split(",")[0].strip()
Path(sys.argv[2]).write_text(
    "[Interface]\n"
    f"PrivateKey = {vals['PrivateKey']}\n"
    f"Address = {addr}\n"
    f"DNS = {dns}\n"
    f"MTU = {vals['MTU']}\n"
    "\n[Peer]\n"
    f"PublicKey = {vals['PublicKey']}\n"
    "AllowedIPs = 0.0.0.0/0\n"
    f"Endpoint = {vals['Endpoint']}\n"
    "PersistentKeepalive = 25\n"
    "\n[Socks5]\n"
    "BindAddress = 127.0.0.1:40000\n"
)
PY

  if [[ -f /tmp/election-wireproxy.pid ]] && kill -0 "$(cat /tmp/election-wireproxy.pid)" 2>/dev/null; then
    kill "$(cat /tmp/election-wireproxy.pid)" 2>/dev/null || true
    sleep 1
  fi
  setsid "$bindir/wireproxy" -c "$workdir/wireproxy.conf" >/tmp/election-wireproxy.log 2>&1 < /dev/null &
  echo $! > /tmp/election-wireproxy.pid
  sleep 1

  local ok=0
  local _
  for _ in $(seq 1 20); do
    code=$(curl -s -o /tmp/election-egress-body -w '%{http_code}' --max-time 25 \
      -x "$socks" \
      -A "$ua" \
      -H "Referer: https://mapvotes.bechirot.gov.il/" \
      "$cec_url" || true)
    if [[ "$code" == 200 ]]; then
      ok=1
      break
    fi
    sleep 1
  done
  # The profile contains a private key. Drop it once the tunnel is up.
  rm -rf "$workdir"
  if [[ "$ok" != 1 ]]; then
    echo "WARP tunnel could not fetch elections.json (last HTTP ${code:-000})"
    head -c 240 /tmp/election-egress-body 2>/dev/null || true
    echo
    tail -n 20 /tmp/election-wireproxy.log 2>/dev/null || true
    return 1
  fi

  export ALL_PROXY="$socks"
  export all_proxy="$socks"
  export https_proxy="$socks"
  export http_proxy="$socks"
  export NO_PROXY="localhost,127.0.0.1"
  echo "WARP tunnel is up; committee JSON is reachable through it"
  cd "$orig"
}

ensure_egress
