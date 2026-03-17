import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
} from "remotion";
import { z } from "zod";

export const insightVideoSchema = z.object({
  topic: z.string(),
  stat: z.string(),
  insight: z.string(),
  contrarian: z.string(),
  cta: z.string(),
});

type Props = z.infer<typeof insightVideoSchema>;

// Slide durations (frames at 30fps)
const INTRO_DURATION = 60;   // 2s
const STAT_DURATION = 90;    // 3s
const INSIGHT_DURATION = 90; // 3s
const CONTRA_DURATION = 90;  // 3s
const CTA_DURATION = 90;     // 3s
// Total: 420 frames = 14s

const BRAND = {
  bg: "#0A0A0A",
  accent: "#C9F31D",       // electric lime — sharp, not flashy
  accentDim: "#8FB814",
  text: "#F5F5F5",
  muted: "#888888",
  font: "system-ui, -apple-system, sans-serif",
};

function fadeIn(frame: number, start: number, duration = 20) {
  return interpolate(frame, [start, start + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
}

// ── Intro slide ──────────────────────────────────────────────────────────────
const IntroSlide: React.FC<{ topic: string }> = ({ topic }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({ fps, frame, config: { damping: 18, stiffness: 120 } });
  const opacity = fadeIn(frame, 10);

  return (
    <AbsoluteFill
      style={{
        background: BRAND.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 80,
        gap: 24,
      }}
    >
      {/* Accent bar */}
      <div
        style={{
          width: interpolate(frame, [0, 30], [0, 120], { extrapolateRight: "clamp" }),
          height: 4,
          background: BRAND.accent,
          borderRadius: 2,
        }}
      />
      <div
        style={{
          opacity,
          transform: `scale(${scale})`,
          fontFamily: BRAND.font,
          fontSize: 52,
          fontWeight: 800,
          color: BRAND.text,
          textAlign: "center",
          lineHeight: 1.15,
          letterSpacing: "-0.02em",
        }}
      >
        {topic}
      </div>
      <div
        style={{
          opacity: fadeIn(frame, 25),
          fontFamily: BRAND.font,
          fontSize: 22,
          fontWeight: 500,
          color: BRAND.accent,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
        }}
      >
        Pietro Piga · AI Sales Advisor
      </div>
    </AbsoluteFill>
  );
};

// ── Stat slide ───────────────────────────────────────────────────────────────
const StatSlide: React.FC<{ stat: string }> = ({ stat }) => {
  const frame = useCurrentFrame();

  // Extract leading number/percentage if present
  const match = stat.match(/^(\d[\d%,\.]+)/);
  const number = match ? match[1] : null;
  const rest = number ? stat.slice(number.length) : stat;

  return (
    <AbsoluteFill
      style={{
        background: BRAND.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: 80,
        gap: 16,
      }}
    >
      <div
        style={{
          opacity: fadeIn(frame, 0),
          fontFamily: BRAND.font,
          fontSize: 18,
          fontWeight: 600,
          color: BRAND.muted,
          textTransform: "uppercase",
          letterSpacing: "0.14em",
        }}
      >
        The number
      </div>
      {number && (
        <div
          style={{
            opacity: fadeIn(frame, 8),
            fontFamily: BRAND.font,
            fontSize: 120,
            fontWeight: 900,
            color: BRAND.accent,
            lineHeight: 1,
            letterSpacing: "-0.04em",
          }}
        >
          {number}
        </div>
      )}
      <div
        style={{
          opacity: fadeIn(frame, number ? 18 : 8),
          fontFamily: BRAND.font,
          fontSize: number ? 36 : 48,
          fontWeight: 700,
          color: BRAND.text,
          lineHeight: 1.3,
          maxWidth: 860,
        }}
      >
        {number ? rest : stat}
      </div>
    </AbsoluteFill>
  );
};

// ── Insight slide ────────────────────────────────────────────────────────────
const InsightSlide: React.FC<{ insight: string }> = ({ insight }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        background: BRAND.accent,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: 80,
        gap: 20,
      }}
    >
      <div
        style={{
          opacity: fadeIn(frame, 0),
          fontFamily: BRAND.font,
          fontSize: 18,
          fontWeight: 600,
          color: "#0A0A0A",
          textTransform: "uppercase",
          letterSpacing: "0.14em",
        }}
      >
        What the data shows
      </div>
      <div
        style={{
          opacity: fadeIn(frame, 10),
          fontFamily: BRAND.font,
          fontSize: 52,
          fontWeight: 800,
          color: "#0A0A0A",
          lineHeight: 1.2,
          letterSpacing: "-0.02em",
        }}
      >
        {insight}
      </div>
    </AbsoluteFill>
  );
};

// ── Contrarian slide ──────────────────────────────────────────────────────────
const ContrarianSlide: React.FC<{ contrarian: string }> = ({ contrarian }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        background: BRAND.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: 80,
        gap: 20,
        borderLeft: `8px solid ${BRAND.accent}`,
      }}
    >
      <div
        style={{
          opacity: fadeIn(frame, 0),
          fontFamily: BRAND.font,
          fontSize: 18,
          fontWeight: 600,
          color: BRAND.accent,
          textTransform: "uppercase",
          letterSpacing: "0.14em",
        }}
      >
        But here's what they don't tell you
      </div>
      <div
        style={{
          opacity: fadeIn(frame, 10),
          fontFamily: BRAND.font,
          fontSize: 50,
          fontWeight: 700,
          color: BRAND.text,
          lineHeight: 1.25,
        }}
      >
        {contrarian}
      </div>
    </AbsoluteFill>
  );
};

// ── CTA slide ─────────────────────────────────────────────────────────────────
const CTASlide: React.FC<{ cta: string }> = ({ cta }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    fps,
    frame,
    config: { damping: 14, stiffness: 100 },
    from: 0.85,
    to: 1,
  });

  return (
    <AbsoluteFill
      style={{
        background: BRAND.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 80,
        gap: 28,
      }}
    >
      <div
        style={{
          opacity: fadeIn(frame, 0, 25),
          transform: `scale(${scale})`,
          fontFamily: BRAND.font,
          fontSize: 50,
          fontWeight: 800,
          color: BRAND.text,
          textAlign: "center",
          lineHeight: 1.3,
        }}
      >
        {cta}
      </div>
      <div
        style={{
          opacity: fadeIn(frame, 20),
          fontFamily: BRAND.font,
          fontSize: 20,
          fontWeight: 600,
          color: BRAND.muted,
        }}
      >
        Pietro Piga · AI Sales Advisor
      </div>
      {/* Bottom accent line */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          width: interpolate(frame, [10, 50], [0, 240], { extrapolateRight: "clamp" }),
          height: 3,
          background: BRAND.accent,
          borderRadius: 2,
        }}
      />
    </AbsoluteFill>
  );
};

// ── Main composition ──────────────────────────────────────────────────────────
export const InsightVideo: React.FC<Props> = ({
  topic,
  stat,
  insight,
  contrarian,
  cta,
}) => {
  return (
    <AbsoluteFill style={{ background: BRAND.bg }}>
      <Sequence from={0} durationInFrames={INTRO_DURATION}>
        <IntroSlide topic={topic} />
      </Sequence>
      <Sequence from={INTRO_DURATION} durationInFrames={STAT_DURATION}>
        <StatSlide stat={stat} />
      </Sequence>
      <Sequence from={INTRO_DURATION + STAT_DURATION} durationInFrames={INSIGHT_DURATION}>
        <InsightSlide insight={insight} />
      </Sequence>
      <Sequence from={INTRO_DURATION + STAT_DURATION + INSIGHT_DURATION} durationInFrames={CONTRA_DURATION}>
        <ContrarianSlide contrarian={contrarian} />
      </Sequence>
      <Sequence from={INTRO_DURATION + STAT_DURATION + INSIGHT_DURATION + CONTRA_DURATION} durationInFrames={CTA_DURATION}>
        <CTASlide cta={cta} />
      </Sequence>
    </AbsoluteFill>
  );
};
