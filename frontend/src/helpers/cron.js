const DOW_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];
const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export function describeCron(min, hour, dom, month, dow) {
  if ([min, hour, dom, month, dow].every((f) => f === "*"))
    return "every minute";

  const parts = [];
  const minIsStep = /^\*\/(\d+)$/.test(min);
  const hourIsStep = /^\*\/(\d+)$/.test(hour);
  const minIsNum = /^\d+$/.test(min);
  const hourIsNum = /^\d+$/.test(hour);

  if (minIsStep) {
    const step = min.match(/^\*\/(\d+)$/)[1];
    parts.push(`every ${step} minutes`);
  } else if (hourIsStep) {
    const step = hour.match(/^\*\/(\d+)$/)[1];
    parts.push(
      minIsNum ? `every ${step} hours at minute ${min}` : `every ${step} hours`,
    );
  } else if (minIsNum && hourIsNum) {
    const h = String(parseInt(hour)).padStart(2, "0");
    const m = String(parseInt(min)).padStart(2, "0");
    parts.push(`at ${h}:${m}`);
  } else if (minIsNum) {
    parts.push(`at minute ${min} past every hour`);
  } else if (hourIsNum) {
    parts.push(`every minute during hour ${hour}`);
  }

  if (dow !== "*") {
    const names = dow.split(",").map((d) => {
      const range = d.match(/^(\d+)-(\d+)$/);
      if (range)
        return `${DOW_NAMES[+range[1]]} through ${DOW_NAMES[+range[2]]}`;
      return DOW_NAMES[+d] ?? d;
    });
    parts.push(`on ${names.join(" and ")}`);
  } else if (dom !== "*") {
    if (/^\*\/(\d+)$/.test(dom)) {
      parts.push(`every ${dom.split("/")[1]} days`);
    } else {
      parts.push(`on day ${dom.split(",").join(" and day ")}`);
    }
  }

  if (month !== "*") {
    if (/^\*\/(\d+)$/.test(month)) {
      parts.push(`every ${month.split("/")[1]} months`);
    } else {
      const names = month.split(",").map((m) => MONTH_NAMES[+m - 1] ?? m);
      parts.push(`in ${names.join(" and ")}`);
    }
  }

  return parts.join(", ") || "custom schedule";
}

/**
 * Parses a Celery schedule string back into an object compatible with ScheduleEditor's
 * initialSchedule prop.
 * Examples:
 *   "<freq: 1.00 minute>"          → { type: "interval", every: 1, unit: "minutes" }
 *   "<crontab: 28 12 * * * (...)>" → { type: "crontab", minute: "28", hour: "12", ... }
 */
export function parseScheduleString(scheduleStr) {
  if (!scheduleStr || typeof scheduleStr !== "string") {
    return { type: "interval", every: 1, unit: "minutes" };
  }

  const freqMatch = scheduleStr.match(/<freq:\s*([\d.]+)\s*(\w+)/);
  if (freqMatch) {
    const value = parseFloat(freqMatch[1]);
    const rawUnit = freqMatch[2].toLowerCase().replace(/s$/, "");
    const unitMap = {
      second: "seconds",
      minute: "minutes",
      hour: "hours",
      day: "days",
    };
    const unit = unitMap[rawUnit] || "seconds";
    if (value % 1 === 0) return { type: "interval", every: value, unit };
    const multipliers = { seconds: 1, minutes: 60, hours: 3600, days: 86400 };
    return {
      type: "interval",
      every: Math.round(value * multipliers[unit]),
      unit: "seconds",
    };
  }

  const crontabMatch = scheduleStr.match(
    /<crontab:\s*([\d*/,\-]+)\s+([\d*/,\-]+)\s+([\d*/,\-]+)\s+([\d*/,\-]+)\s+([\d*/,\-]+)/,
  );
  if (crontabMatch) {
    const [, minute, hour, dayOfMonth, month, dayOfWeek] = crontabMatch;
    return { type: "crontab", minute, hour, dayOfMonth, month, dayOfWeek };
  }

  return { type: "interval", every: 1, unit: "minutes" };
}

/**
 * Converts a Celery schedule string (from str(task.schedule)) to a human-readable label.
 * Examples:
 *   "<freq: 1.00 minute>"          → "every 1 minute"
 *   "<freq: 30.00 seconds>"        → "every 30 seconds"
 *   "<crontab: 28 12 * * * (...)>" → "at 12:28"
 */
export function formatSchedule(scheduleStr) {
  if (!scheduleStr) return "-";

  const freqMatch = scheduleStr.match(/<freq:\s*([\d.]+)\s*(\w+)>/);
  if (freqMatch) {
    const value = parseFloat(freqMatch[1]);
    const unit = freqMatch[2];
    const display =
      value % 1 === 0 ? String(value) : value.toFixed(2).replace(/\.?0+$/, "");
    return `every ${display} ${value === 1 ? unit : unit + "s"}`;
  }

  const crontabMatch = scheduleStr.match(
    /<crontab:\s*([\d*/,\-]+)\s+([\d*/,\-]+)\s+([\d*/,\-]+)\s+([\d*/,\-]+)\s+([\d*/,\-]+)/,
  );
  if (crontabMatch) {
    const [, min, hour, dom, month, dow] = crontabMatch;
    return describeCron(min, hour, dom, month, dow);
  }

  return scheduleStr;
}
