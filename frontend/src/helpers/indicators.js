/**
 * Recognise what an indicator typed into a form is.
 *
 * Values are often pasted defanged (hxxps://evil[.]com, 1.2.3[.]4,
 * bob[@]example.com). They are refanged before being recognised: the
 * attributes ingest pipeline refangs them the same way when stored (see
 * api/app/services/normalisation/normalise.painless), so the type detected
 * is the type of the value that will be stored.
 */
import { detectJa4Variant } from "@/helpers/ja4";

const REFANGS = [
  ["[://]", "://"],
  ["[:]", ":"],
  ["[.]", "."],
  ["(.)", "."],
  ["{.}", "."],
  ["[dot]", "."],
  ["[DOT]", "."],
  ["(dot)", "."],
  ["(DOT)", "."],
  ["[@]", "@"],
  ["[at]", "@"],
  ["[AT]", "@"],
];

/** The value with defanging undone (hxxp, [.], [@], ...). */
export function refang(value) {
  let v = value;
  const lower = v.toLowerCase();
  if (lower.startsWith("hxxp")) v = "http" + v.slice(4);
  else if (lower.startsWith("fxp")) v = "ftp" + v.slice(3);
  for (const [from, to] of REFANGS) v = v.split(from).join(to);
  return v;
}

function isIpv4(v) {
  const parts = v.split(".");
  return (
    parts.length === 4 &&
    parts.every((p) => /^\d{1,3}$/.test(p) && Number(p) <= 255)
  );
}

function isIpv6(v) {
  if (!v.includes(":") || !/^[0-9a-fA-F:.]+$/.test(v)) return false;
  try {
    // The URL parser validates IPv6 literals, IPv4-mapped ones included.
    new URL(`http://[${v}]/`);
    return true;
  } catch {
    return false;
  }
}

function isIp(v) {
  const [address, prefix, ...rest] = v.split("/");
  if (rest.length) return false;
  if (prefix !== undefined) {
    if (!/^\d{1,3}$/.test(prefix)) return false;
    const max = address.includes(":") ? 128 : 32;
    if (Number(prefix) > max) return false;
  }
  return isIpv4(address) || isIpv6(address);
}

const HASHES = [
  [32, "md5", "MD5 hash"],
  [40, "sha1", "SHA-1 hash"],
  [56, "sha224", "SHA-224 hash"],
  [64, "sha256", "SHA-256 hash"],
  [96, "sha384", "SHA-384 hash"],
  [128, "sha512", "SHA-512 hash"],
];

const DOMAIN =
  /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}\.?$/;

/**
 * What a value is: `{type, category, label, defanged, value}`, where
 * `value` is the refanged value (what will be stored) and `defanged` says
 * whether that differs from what was typed. Null when nothing matches.
 */
export function detectAttribute(input) {
  if (!input) return null;
  const typed = input.trim();
  if (!typed) return null;
  const v = refang(typed);
  const result = (type, category, label) => ({
    type,
    category,
    label,
    value: v,
    defanged: v !== typed,
  });

  if (/^[a-fA-F0-9]+$/.test(v)) {
    const hash = HASHES.find(([length]) => length === v.length);
    if (hash) return result(hash[1], "Payload delivery", hash[2]);
  }

  if (isIp(v)) {
    return result(
      "ip-dst",
      "Network activity",
      v.includes("/") ? "IP range" : "IP address",
    );
  }

  // 203.0.113.5:8080, [2001:db8::1]:443
  const ipPort = v.match(/^\[?([0-9a-fA-F:.]+?)\]?:(\d{1,5})$/);
  if (
    ipPort &&
    Number(ipPort[2]) <= 65535 &&
    (isIpv4(ipPort[1]) || (v.startsWith("[") && isIpv6(ipPort[1])))
  ) {
    return result("ip-dst|port", "Network activity", "IP address and port");
  }

  if (/^(?:https?|ftp):\/\//i.test(v)) {
    return result("url", "Network activity", "URL");
  }

  if (/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) {
    return result("email-src", "Payload delivery", "Email address");
  }

  if (/^(?:CVE-\d{4}-\d{4,}|GCVE-0-\d{4}-\d{4,})$/i.test(v)) {
    return result("vulnerability", "External analysis", "Vulnerability");
  }

  if (DOMAIN.test(v)) {
    return result("domain", "Network activity", "Domain");
  }

  const ja4 = detectJa4Variant(v);
  if (ja4) {
    return result("text", "Network activity", `${ja4} fingerprint`);
  }

  return null;
}
