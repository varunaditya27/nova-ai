import { ImageResponse } from "next/og";

export const alt = "Nova — intelligence that remembers";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** The share card — the warm-study world in one image: ivory, the brass mark, the belief. */
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#F4F1EA",
          color: "#1A1714",
          padding: "80px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {/* The Nova mark, drawn inline */}
          <svg width="40" height="40" viewBox="0 0 32 32" fill="none">
            <circle
              cx="16"
              cy="16"
              r="11"
              stroke="#9A7B4F"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeDasharray="60 9.3"
              transform="rotate(-96 16 16)"
            />
            <circle cx="16" cy="16" r="4.4" fill="#9A7B4F" />
          </svg>
          <span style={{ fontSize: 30, letterSpacing: "0.02em" }}>Nova</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 68, lineHeight: 1.1, letterSpacing: "-0.02em", maxWidth: 900 }}>
            Intelligence should feel like a relationship, not a tool.
          </div>
          <div style={{ fontSize: 26, color: "#4A443C", marginTop: 28 }}>
            It remembers. It notices. It continues.
          </div>
        </div>

        <div
          style={{
            fontSize: 18,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
            color: "#8B8377",
          }}
        >
          A private study for thinking
        </div>
      </div>
    ),
    { ...size }
  );
}
