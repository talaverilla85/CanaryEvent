/* D’Parranda: Canary-local date/time rules for upcoming and ongoing events.
 * The server serializes event.start/end as local wall-clock ISO strings without offsets.
 * Pass "YYYY-MM-DDTHH:mm" computed with Intl timeZone: "Atlantic/Canary".
 * No Date.parse on these event strings: visitors may be in another timezone.
 */
(function (root) {
  'use strict';
  const isoMinute = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)
    ? value.slice(0, 16) : '';
  const isoDate = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}/.test(value)
    ? value.slice(0, 10) : '';

  function hasFinished(event, canaryNow) {
    const startDate = isoDate(event && event.start);
    const nowDate = isoDate(canaryNow);
    if (!startDate || !nowDate) return true;
    const startTime = isoMinute(event.start);
    const endDate = isoDate(event.end) || startDate;
    const endTime = isoMinute(event.end);
    const nowMinute = isoMinute(canaryNow);
    if (endDate < nowDate) return true;
    // An explicit finish time is authoritative, even when the start was earlier.
    if (endTime) return !!nowMinute && endTime <= nowMinute;
    // A multi-day range without a known finish time remains available through
    // its last calendar day. We must not invent a daily session or closing hour.
    if (endDate > startDate) return false;
    // One-off timed events without a verified end stop being suggested once begun.
    // An optional date-only "end" on that same day does NOT establish duration.
    return !!startTime && !!nowMinute && startTime < nowMinute;
  }

  function isInProgress(event, canaryNow) {
    const start = isoMinute(event && event.start);
    const end = isoMinute(event && event.end);
    const now = isoMinute(canaryNow);
    return !!(start && end && now && start <= now && now < end);
  }

  function hasUnconfirmedHours(event, canaryNow) {
    const start = isoMinute(event && event.start);
    const date = isoDate(canaryNow);
    // All-day and multi-day programmes with date ranges cannot be treated as
    // a guaranteed session at the clock time the person opens the app.
    return !start || (isoDate(event.start) < date && !isoMinute(event.end));
  }

  const api = Object.freeze({hasFinished, isInProgress, hasUnconfirmedHours});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.DParrandaTime = api;
})(typeof window !== 'undefined' ? window : globalThis);
