// An organisation warninglist's sync schedule (sync_every_minutes), in words.
export function describeSyncSchedule(minutes) {
  if (!minutes) return "manually";
  if (minutes === 60) return "hourly";
  if (minutes === 1440) return "daily";
  if (minutes === 10080) return "weekly";
  if (minutes % 1440 === 0) return `every ${minutes / 1440} days`;
  if (minutes % 60 === 0) return `every ${minutes / 60} hours`;
  return `every ${minutes} minutes`;
}
