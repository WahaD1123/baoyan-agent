import { Section } from "../components/Section";
import type { StudentProfile } from "../types/domain";

type Props = {
  profile: StudentProfile;
  plan: string;
  schools: string[];
  timeline: string[];
  onGenerate: () => void;
};

export function PlanningPage({ profile, plan, schools, timeline, onGenerate }: Props) {
  return (
    <Section
      title="院校规划"
      eyebrow="申请策略"
      description={`${profile.name} / Top ${profile.rank_percent}% / ${profile.research_interests.join(", ")}`}
      actions={<button onClick={onGenerate}>生成规划</button>}
    >
      <div className="contentGrid">
        <div className="panel">
          <h3>推荐梯度</h3>
          {schools.length ? (
            <ul className="plainList">
              {schools.map((school) => <li key={school}>{school}</li>)}
            </ul>
          ) : <p className="emptyText">生成后会展示冲刺、稳妥和保底院校策略。</p>}
        </div>
        <div className="panel">
          <h3>准备节奏</h3>
          {timeline.length ? (
            <ul className="plainList">
              {timeline.map((item) => <li key={item}>{item}</li>)}
            </ul>
          ) : <p className="emptyText">生成后会展示材料准备、联系导师和面试练习的节奏。</p>}
        </div>
      </div>
      <div className="answerPanel light">
        <pre>{plan}</pre>
      </div>
    </Section>
  );
}
