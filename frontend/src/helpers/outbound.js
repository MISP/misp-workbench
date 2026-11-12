// Early feedback on a feed's or MISP server's URL, mirroring the API's
// outbound rules (app/services/outbound.py), which stay the authority: the
// browser can't resolve a name, so only what the URL itself says is checked.
import { ref } from "vue";
import { fetchWrapper } from "@/helpers/fetch-wrapper";

const WHAT = {
  feeds: "feeds may fetch from",
  servers: "MISP servers may connect to",
};

function ipv4(host) {
  const parts = host.split(".");
  if (parts.length !== 4) return null;
  const octets = parts.map((p) => (/^\d{1,3}$/.test(p) ? Number(p) : NaN));
  return octets.every((o) => o >= 0 && o <= 255) ? octets : null;
}

function forbiddenIpv4([a, b]) {
  return (
    a === 127 || // loopback
    a === 0 || // unspecified ("this network")
    (a === 169 && b === 254) || // link-local: cloud metadata
    a >= 224 // multicast, reserved
  );
}

/** Whether `host` (as URL.hostname gives it) is an address no fetch may reach. */
export function forbiddenHost(host) {
  const name = String(host || "")
    .toLowerCase()
    .replace(/^\[|\]$/g, "");
  if (name === "localhost" || name.endsWith(".localhost")) return true;
  const v4 = ipv4(name);
  if (v4) return forbiddenIpv4(v4);
  if (!name.includes(":")) return false;
  // IPv6: loopback, unspecified, link-local, multicast, IPv4-mapped.
  if (name === "::1" || name === "::") return true;
  if (/^fe[89ab]/.test(name) || name.startsWith("ff")) return true;
  const mapped = /^::ffff:(.+)$/.exec(name);
  if (mapped) {
    const inner = ipv4(mapped[1]);
    if (inner) return forbiddenIpv4(inner);
    // URL() writes ::ffff:127.0.0.1 as ::ffff:7f00:1.
    const hex = /^([0-9a-f]{1,4}):([0-9a-f]{1,4})$/.exec(mapped[1]);
    if (hex) {
      const hi = parseInt(hex[1], 16);
      return forbiddenIpv4([hi >> 8, hi & 255]);
    }
  }
  return false;
}

/** fnmatch-style: `*` any run of characters, `?` one, case-insensitive. */
export function hostMatches(host, pattern) {
  const source = String(pattern)
    .toLowerCase()
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replace(/\*/g, ".*")
    .replace(/\?/g, ".");
  return new RegExp(`^${source}$`).test(String(host).toLowerCase());
}

/**
 * What is wrong with `url` as a `kind` ("feeds", "servers") destination, or
 * null. `hosts` is the allowlist (null while unknown: only the URL itself is
 * checked); empty allows any host.
 */
export function sourceUrlProblem(url, hosts, kind) {
  const text = String(url || "").trim();
  if (!text) return null;
  let parsed;
  try {
    parsed = new URL(text);
  } catch {
    return "Not a URL: write it with http:// or https://";
  }
  if (!["http:", "https:"].includes(parsed.protocol) || !parsed.hostname) {
    return "The URL must be http(s), with a host";
  }
  const host = parsed.hostname.toLowerCase();
  if (forbiddenHost(host)) {
    return `${host} is an address the server may never fetch from (loopback, link-local, multicast or reserved)`;
  }
  if (hosts?.length && !hosts.some((p) => hostMatches(host, p))) {
    return `${host} isn't a host ${WHAT[kind] || "the server may fetch from"}; an admin allows hosts in the runtime settings (${kind}.source_hosts)`;
  }
  return null;
}

// The allowlist per kind, fetched once per page load.
const allowed = {};

/** A ref to `kind`'s allowed hosts: null until known (or if unreadable). */
export function useAllowedHosts(kind) {
  if (!allowed[kind]) {
    allowed[kind] = ref(null);
    fetchWrapper
      .get(`${import.meta.env.VITE_API_URL}/${kind}/sources`)
      .then((response) => (allowed[kind].value = response?.hosts ?? []))
      .catch(() => {});
  }
  return allowed[kind];
}
