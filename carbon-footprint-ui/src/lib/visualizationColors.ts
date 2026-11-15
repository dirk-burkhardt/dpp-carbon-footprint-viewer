let useDark = false;

type Color = [lightModeRgb: [number, number, number], darkModeRgb?: [number, number, number]]

const colors = {
  "pcf": [[237, 237, 237], [237, 237, 237]],
  "tcf": [[209, 209, 209]],
  "cf": [[223, 223, 223]],
} as const satisfies Record<string, Color>;

export default function c(surfaceName: keyof typeof colors): [number, number, number] {
  return useDark ? colors[surfaceName][1] || colors[surfaceName][0] : colors[surfaceName][0];
}

export function colorString(surfaceName: keyof typeof colors): string {
  return `rgb(${c(surfaceName).join(",")})`;
}

export function set(mode: "light" | "dark") {
  useDark = mode === "dark";
}
