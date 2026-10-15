<script setup>
// Options of the detection-engine formats: the rules' action and the
// zone's policy. Two-way bound: { rule_action, rpz_policy, rpz_redirect }.
const props = defineProps({
  format: { type: String, required: true },
  idPrefix: { type: String, default: "export" },
});
const options = defineModel({ type: Object, required: true });
</script>

<template>
  <div v-if="props.format === 'suricata'">
    <label class="form-label" :for="`${props.idPrefix}-rule-action`"
      >Rule action</label
    >
    <select
      :id="`${props.idPrefix}-rule-action`"
      v-model="options.rule_action"
      class="form-select"
    >
      <option value="alert">alert</option>
      <option value="drop">drop (IPS mode)</option>
    </select>
    <div class="form-text">
      IP rules for addresses and networks; DNS, TLS SNI and HTTP Host rules for
      domains (subdomains included) and hostnames; HTTP rules for
      <code>http://</code> URLs and user agents; JA3 rules for JA3 fingerprints.
      Each rule's SID is derived from what it matches, so it stays the same from
      one run to the next. Load it with <code>suricata -S</code> or list it in
      <code>rule-files</code>.
    </div>
  </div>
  <div v-else-if="props.format === 'zeek'" class="form-text">
    A Zeek Intel framework file: addresses, networks, domains, URLs, file hashes
    and names, e-mail addresses, certificate hashes and user agents. Add it to
    <code>Intel::read_files</code>.
  </div>
  <div v-else-if="props.format === 'rpz'">
    <div class="row g-2">
      <div class="col-md-6">
        <label class="form-label" :for="`${props.idPrefix}-rpz-policy`"
          >Answer</label
        >
        <select
          :id="`${props.idPrefix}-rpz-policy`"
          v-model="options.rpz_policy"
          class="form-select"
        >
          <option value="nxdomain">NXDOMAIN</option>
          <option value="nodata">NODATA</option>
          <option value="drop">No answer (drop)</option>
          <option value="redirect">Walled garden (CNAME)</option>
        </select>
      </div>
      <div v-if="options.rpz_policy === 'redirect'" class="col-md-6">
        <label class="form-label" :for="`${props.idPrefix}-rpz-redirect`"
          >Walled garden</label
        >
        <input
          :id="`${props.idPrefix}-rpz-redirect`"
          v-model="options.rpz_redirect"
          class="form-control font-monospace"
          placeholder="blocked.example.org"
        />
      </div>
    </div>
    <div class="form-text">
      A Response Policy Zone for BIND, Unbound, PowerDNS or Infoblox. Domains
      cover their subdomains, hostnames themselves only, and addresses are
      <code>rpz-ip</code> triggers for answers resolving to them. The serial is
      the time of the run.
    </div>
  </div>
</template>
