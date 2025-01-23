export const tagHelper = {
  getContrastColor,
  getBackgroundColor,
  getTag,
};

function getTag(namspace, tag) {
  if (!tag) return "";

  if (!namspace) return tag;

  return `${namspace}:${tag}`;
}

function getBackgroundColor(hex) {
  if (!hex) return "#DDD";
  return hex;
}

function getContrastColor(hex) {
  if (!hex) return "#000000";

  hex = hex.replace("#", "");

  // Convert the hex color to RGB
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);

  // Calculate the luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

  // If luminance is high, use black text; otherwise, use white text
  return luminance > 0.5 ? "#000000" : "#FFFFFF";
}
