import type { StudentProfile } from "../types/domain";
import { Section } from "../components/Section";

type Props = {
  profile: StudentProfile;
};

export function ProfilePage({ profile }: Props) {
  return (
    <Section title="用户画像" eyebrow="Member A">
      <div className="metrics">
        <div>
          <span>学生</span>
          <strong>{profile.name}</strong>
        </div>
        <div>
          <span>学校专业</span>
          <strong>{profile.university} / {profile.major}</strong>
        </div>
        <div>
          <span>排名</span>
          <strong>Top {profile.rank_percent}%</strong>
        </div>
      </div>
      <div className="twoColumn">
        <div>
          <h3>研究兴趣</h3>
          <div className="tagRow">
            {profile.research_interests.map((item) => <span key={item}>{item}</span>)}
          </div>
        </div>
        <div>
          <h3>项目经历</h3>
          <ul className="plainList">
            {profile.projects.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      </div>
    </Section>
  );
}
