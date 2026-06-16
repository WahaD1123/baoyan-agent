import type { StudentProfile } from "../types/domain";
import { Section } from "../components/Section";

type Props = {
  profile: StudentProfile;
  plan: string;
  schools: string[];
  timeline: string[];
  onGenerate: () => void;
};

export function PlanningPage({ profile, plan, schools, timeline, onGenerate }: Props) {
  return (
    <Section title="申请规划" eyebrow="Workflow" actions={<button onClick={onGenerate}>生成规划</button>}>
      <div className="split">
        <div>
          <h3>推荐策略</h3>
          <ul className="plainList">
            {schools.map((school) => <li key={school}>{school}</li>)}
          </ul>
        </div>
        <div>
          <h3>时间线</h3>
          <ul className="plainList">
            {timeline.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      </div>
      <p className="muted">当前画像：{profile.name}, Top {profile.rank_percent}%, {profile.research_interests.join(", ")}</p>
      <pre className="resultBox">{plan}</pre>
    </Section>
  );
}
