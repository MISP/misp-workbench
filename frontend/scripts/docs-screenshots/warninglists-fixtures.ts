/**
 * Stub data for the warninglists screenshots. The list mirrors real MISP
 * warninglists (names, types, entry counts); the screenshot environment
 * doesn't load the 6.4M real entries, and a dev instance may have all or
 * none of them, so the page is served from here for reproducible captures.
 */
const updated = "2026-10-01T08:00:00Z";

const list = (
  id: number,
  name: string,
  type: string,
  entry_count: number,
  matching_attributes: string[],
  description: string,
  enabled = true,
) => ({
  id,
  name,
  description,
  type,
  category: "false-positive",
  version: 20261001,
  matching_attributes,
  entry_count,
  enabled,
  updated_at: updated,
});

const IP_TYPES = [
  "ip-src",
  "ip-dst",
  "domain|ip",
  "ip-src|port",
  "ip-dst|port",
];
const HOST_TYPES = ["hostname", "domain", "url", "domain|ip"];

export const WARNINGLISTS = [
  list(
    1,
    "Captive Portal Detection Hostnames",
    "hostname",
    41,
    HOST_TYPES,
    "Hostnames operating systems and browsers query to detect captive portals",
  ),
  list(
    2,
    "List of known IPv4 public DNS resolvers",
    "string",
    66,
    IP_TYPES,
    "Event contains one or more public IPv4 DNS resolvers as attribute with an IDS flag set",
  ),
  list(
    3,
    "List of known google domains",
    "hostname",
    210,
    HOST_TYPES,
    "Known Google domains, as published by Google",
  ),
  list(
    4,
    "List of RFC 1918 CIDR blocks",
    "cidr",
    3,
    IP_TYPES,
    "Private IPv4 address space (RFC 1918)",
  ),
  list(
    5,
    "List of RFC 5735 CIDR blocks",
    "cidr",
    14,
    IP_TYPES,
    "Special use IPv4 addresses (RFC 5735)",
  ),
  list(
    6,
    "List of known Amazon AWS IP address ranges",
    "cidr",
    9812,
    IP_TYPES,
    "Amazon AWS IP address ranges",
  ),
  list(
    7,
    "Top 1,000,000 most-used sites from Tranco",
    "hostname",
    1_000_000,
    HOST_TYPES,
    "Event contains one or more entries from the top 1,000,000 most-used sites",
  ),
  list(
    8,
    "Top 10K most-used sites from Tranco",
    "hostname",
    10_000,
    HOST_TYPES,
    "Event contains one or more entries from the top 10K most-used sites",
  ),
  list(
    9,
    "List of known hashes with common false-positives (based on Florian Roth input list)",
    "string",
    64,
    ["md5", "sha1", "sha256", "sha512"],
    "Hashes that are often included in IOC lists but are false positives",
  ),
  list(
    10,
    "Specialized list of vpn-ipv4 addresses belonging to common VPN providers and datacenters",
    "cidr",
    14_211,
    IP_TYPES,
    "VPN providers and datacenters IPv4 address ranges",
    false,
  ),
];

export const CHECK_RESULT = {
  hits: {
    "8.8.8.8": ["List of known IPv4 public DNS resolvers"],
    "www.google.com": [
      "List of known google domains",
      "Top 1,000,000 most-used sites from Tranco",
      "Top 10K most-used sites from Tranco",
    ],
    "10.0.0.5": [
      "List of RFC 1918 CIDR blocks",
      "List of RFC 5735 CIDR blocks",
    ],
  },
};

/** Indicators a partner report often drags in, and the lists they hit. */
export const WARNINGLISTED_ATTRIBUTES = [
  {
    type: "ip-dst",
    value: "8.8.8.8",
    comment: "Resolver the lure page probes before redirecting",
    warninglist_hits: ["List of known IPv4 public DNS resolvers"],
  },
  {
    type: "domain",
    value: "www.google.com",
    comment: "Connectivity check made by the dropper",
    warninglist_hits: [
      "List of known google domains",
      "Top 1,000,000 most-used sites from Tranco",
      "Top 10K most-used sites from Tranco",
    ],
  },
  {
    type: "ip-src",
    value: "192.168.56.101",
    comment: "Sandbox VM address copied from the analysis report",
    warninglist_hits: [
      "List of RFC 1918 CIDR blocks",
      "List of RFC 5735 CIDR blocks",
    ],
  },
];
