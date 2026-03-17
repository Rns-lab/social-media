import { Composition } from "remotion";
import { InsightVideo, insightVideoSchema } from "./InsightVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="InsightVideo"
      component={InsightVideo}
      durationInFrames={420} // 14s: 2s intro + 3s stat + 3s insight + 3s contrarian + 3s CTA
      fps={30}
      width={1080}
      height={1080}
      schema={insightVideoSchema}
      defaultProps={{
        topic: "AI Agents in Enterprise",
        stat: "67% of PE firms will use AI agents for deal sourcing by 2026",
        insight: "The firms that deploy agents for due diligence cut analysis time from 3 weeks to 4 days.",
        contrarian: "But 80% of implementations fail in year 1 — not from bad tech, from bad processes.",
        cta: "Drop a comment → I'll DM you the implementation playbook",
      }}
    />
  );
};
