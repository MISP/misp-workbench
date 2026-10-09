/**
 * Stub data for the sinks screenshots. Delivery status needs a sinks worker
 * and reachable SIEMs, neither of which the screenshot environment has, so
 * the list is served from here. Timestamps are relative to the capture time
 * so "12 minutes ago" reads the same on every run.
 */
const minutesAgo = (n: number) =>
  new Date(Date.now() - n * 60_000).toISOString();

const FILTERS = {
  to_ids_only: true,
  types: [] as string[],
  tags: [] as string[],
  exclude_tags: ["tlp:red"],
  exclude_warninglisted: true,
};

export function sinksList() {
  return [
    {
      id: 1,
      name: "Splunk production",
      type: "splunk_hec",
      enabled: true,
      config: {
        url: "https://splunk.example.org:8088/services/collector/event",
        token: "********",
        index: "threat_intel",
        sourcetype: "misp:attribute",
        source: "misp-workbench",
        verify_tls: true,
        ca_cert: null,
      },
      filters: {
        ...FILTERS,
        types: ["ip-src", "ip-dst", "domain", "url", "sha256"],
      },
      created_at: minutesAgo(60 * 24 * 30),
      updated_at: minutesAgo(60 * 24 * 2),
      last_attempt_at: minutesAgo(12),
      last_success_at: minutesAgo(12),
      last_error: null,
      last_error_at: null,
      delivered_count: 18342,
      failed_count: 0,
    },
    {
      id: 2,
      name: "Graylog SOC",
      type: "gelf",
      enabled: true,
      config: {
        host: "graylog.example.org",
        port: 12201,
        tls: true,
        verify_tls: true,
        ca_cert: null,
      },
      filters: { ...FILTERS, tags: ["tlp:green", "tlp:clear"] },
      created_at: minutesAgo(60 * 24 * 20),
      updated_at: minutesAgo(60 * 24 * 20),
      last_attempt_at: minutesAgo(95),
      last_success_at: minutesAgo(95),
      last_error: null,
      last_error_at: null,
      delivered_count: 4210,
      failed_count: 0,
    },
    {
      id: 3,
      name: "Wazuh syslog",
      type: "syslog",
      enabled: true,
      config: {
        host: "wazuh.example.org",
        port: 514,
        protocol: "tcp",
        tls: false,
        verify_tls: true,
        ca_cert: null,
        hostname: "misp-workbench",
      },
      filters: { ...FILTERS, types: ["ip-src", "ip-dst", "domain"] },
      created_at: minutesAgo(60 * 24 * 10),
      updated_at: minutesAgo(60 * 24 * 10),
      last_attempt_at: minutesAgo(30),
      last_success_at: minutesAgo(60 * 24),
      last_error:
        "cannot connect to wazuh.example.org:514: [Errno 111] Connection refused",
      last_error_at: minutesAgo(30),
      delivered_count: 962,
      failed_count: 2,
    },
    {
      id: 4,
      name: "SOAR webhook",
      type: "webhook",
      enabled: false,
      config: {
        url: "https://soar.example.org/hooks/misp",
        secret: "********",
        verify_tls: true,
        ca_cert: null,
      },
      filters: { ...FILTERS, to_ids_only: false },
      created_at: minutesAgo(60 * 24 * 3),
      updated_at: minutesAgo(60 * 24 * 3),
      last_attempt_at: null,
      last_success_at: null,
      last_error: null,
      last_error_at: null,
      delivered_count: 0,
      failed_count: 0,
    },
  ];
}
