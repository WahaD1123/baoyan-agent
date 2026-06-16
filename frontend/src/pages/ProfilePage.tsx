import { Section } from "../components/Section";
import type { StudentProfile } from "../types/domain";

type Props = {
  profile: StudentProfile;
};

export function ProfilePage({ profile }: Props) {
  return (
    <Section title="我的画像" eyebrow="申请基础" description="这些信息会用于院校规划、导师匹配和申请材料生成。">
      <div className="metricGrid">
        <div className="metricTile">
          <span>学生</span>
          <strong>{profile.name}</strong>
        </div>
        <div className="metricTile">
          <span>学校专业</span>
          <strong>{profile.university} / {profile.major}</strong>
        </div>
        <div className="metricTile">
          <span>专业排名</span>
          <strong>Top {profile.rank_percent}%</strong>
        </div>
      </div>
      <div className="contentGrid">
        <div className="panel">
          <h3>研究兴趣</h3>
          <div className="tagRow">
            {profile.research_interests.map((item) => <span key={item}>{item}</span>)}
          </div>
        </div>
        <div className="panel">
          <h3>项目经历</h3>
          <ul className="plainList">
            {profile.projects.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      </div>
    </Section>
  );
}
