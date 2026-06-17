import { useEffect, useState } from "react";
import { Section } from "../components/Section";
import type { ProfileAnalysis, StudentProfile } from "../types/domain";

type Props = {
  profile: StudentProfile;
  analysis: ProfileAnalysis | null;
  saving: boolean;
  analyzing: boolean;
  planning: boolean;
  onProfileChange: (profile: StudentProfile) => void;
  onSave: (profile: StudentProfile) => Promise<void>;
  onAnalyze: (profile: StudentProfile) => Promise<void>;
  onStartPlanning: () => Promise<void>;
};

export function ProfilePage({
  profile,
  analysis,
  saving,
  analyzing,
  planning,
  onProfileChange,
  onSave,
  onAnalyze,
  onStartPlanning,
}: Props) {
  const [draft, setDraft] = useState<StudentProfile>(profile);

  useEffect(() => {
    setDraft(profile);
  }, [profile]);

  function updateField<K extends keyof StudentProfile>(key: K, value: StudentProfile[K]) {
    const next = { ...draft, [key]: value, updated_at: new Date().toISOString() };
    setDraft(next);
    onProfileChange(next);
  }

  function updateListField<K extends "research_interests" | "projects" | "competitions" | "publications" | "target_regions" | "preferred_schools">(
    key: K,
    value: string
  ) {
    updateField(
      key,
      value
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean) as StudentProfile[K]
    );
  }

  return (
    <Section
      title="个人背景"
      eyebrow="第 1 步"
      description="把你的核心背景补充完整，系统会先分析竞争力，再生成院校梯度和准备建议。"
      actions={
        <>
          <button className="ghostButton darkGhost" onClick={() => void onSave(draft)} disabled={saving}>
            {saving ? "保存中..." : "保存背景"}
          </button>
          <button onClick={() => void onAnalyze(draft)} disabled={analyzing}>
            {analyzing ? "分析中..." : "分析背景"}
          </button>
          <button className="secondary" onClick={() => void onStartPlanning()} disabled={planning}>
            {planning ? "生成中..." : "一键生成规划"}
          </button>
        </>
      }
    >
      <div className="profileLayout">
        <div className="profileForm">
          <div className="contentGrid">
            <div className="stackForm">
              <label>姓名</label>
              <input value={draft.name} onChange={(event) => updateField("name", event.target.value)} />
            </div>
            <div className="stackForm">
              <label>本科院校</label>
              <input value={draft.university} onChange={(event) => updateField("university", event.target.value)} />
            </div>
            <div className="stackForm">
              <label>专业</label>
              <input value={draft.major} onChange={(event) => updateField("major", event.target.value)} />
            </div>
            <div className="stackForm">
              <label>专业排名百分比</label>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={draft.rank_percent}
                onChange={(event) => updateField("rank_percent", Number(event.target.value))}
              />
            </div>
            <div className="stackForm">
              <label>绩点</label>
              <input
                type="number"
                min={0}
                max={4.5}
                step={0.01}
                value={draft.gpa}
                onChange={(event) => updateField("gpa", Number(event.target.value))}
              />
            </div>
            <div className="stackForm">
              <label>英语成绩</label>
              <input
                value={draft.english_score}
                onChange={(event) => updateField("english_score", event.target.value)}
                placeholder="例如 CET-6 523 / IELTS 6.5"
              />
            </div>
            <div className="stackForm">
              <label>申请偏好</label>
              <select
                value={draft.risk_preference}
                onChange={(event) =>
                  updateField("risk_preference", event.target.value as StudentProfile["risk_preference"])
                }
              >
                <option value="conservative">稳妥优先</option>
                <option value="balanced">平衡推进</option>
                <option value="aggressive">冲刺优先</option>
              </select>
            </div>
            <div className="stackForm">
              <label>目标学位</label>
              <select
                value={draft.target_degree}
                onChange={(event) => updateField("target_degree", event.target.value)}
              >
                <option value="master">硕士</option>
                <option value="phd">直博 / 硕博</option>
              </select>
            </div>
          </div>

          <div className="contentGrid">
            <div className="stackForm">
              <label>研究兴趣</label>
              <textarea
                rows={4}
                value={draft.research_interests.join("\n")}
                onChange={(event) => updateListField("research_interests", event.target.value)}
                placeholder="每行一个方向，例如：机器学习"
              />
            </div>
            <div className="stackForm">
              <label>目标城市或地区</label>
              <textarea
                rows={4}
                value={draft.target_regions.join("\n")}
                onChange={(event) => updateListField("target_regions", event.target.value)}
                placeholder="每行一个，例如：上海"
              />
            </div>
            <div className="stackForm">
              <label>项目经历</label>
              <textarea
                rows={5}
                value={draft.projects.join("\n")}
                onChange={(event) => updateListField("projects", event.target.value)}
                placeholder="每行一个项目"
              />
            </div>
            <div className="stackForm">
              <label>竞赛经历</label>
              <textarea
                rows={5}
                value={draft.competitions.join("\n")}
                onChange={(event) => updateListField("competitions", event.target.value)}
                placeholder="每行一个奖项或竞赛"
              />
            </div>
            <div className="stackForm">
              <label>论文或投稿</label>
              <textarea
                rows={4}
                value={draft.publications.join("\n")}
                onChange={(event) => updateListField("publications", event.target.value)}
                placeholder="每行一条"
              />
            </div>
            <div className="stackForm">
              <label>偏好院校</label>
              <textarea
                rows={4}
                value={draft.preferred_schools.join("\n")}
                onChange={(event) => updateListField("preferred_schools", event.target.value)}
                placeholder="每行一个学校"
              />
            </div>
          </div>

          <div className="stackForm">
            <label>补充说明</label>
            <textarea
              rows={4}
              value={draft.notes}
              onChange={(event) => updateField("notes", event.target.value)}
              placeholder="例如科研方向、目标实验室偏好、担心的短板等"
            />
          </div>
        </div>

        <div className="profileSummary">
          <div className="metricGrid">
            <div className="metricTile">
              <span>专业排名</span>
              <strong>Top {draft.rank_percent}%</strong>
            </div>
            <div className="metricTile">
              <span>绩点</span>
              <strong>{draft.gpa.toFixed(2)}</strong>
            </div>
            <div className="metricTile">
              <span>英语成绩</span>
              <strong>{draft.english_score}</strong>
            </div>
          </div>

          <div className="panel accentPanel">
            <h3>当前摘要</h3>
            <p className="summaryText">
              {draft.name}，{draft.university} {draft.major}，关注 {draft.research_interests.join(" / ") || "待补充"}。
            </p>
            <div className="tagRow">
              {draft.preferred_schools.slice(0, 4).map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </div>

          <div className="panel">
            <h3>画像分析</h3>
            {analysis ? (
              <>
                <div className="scoreStrip">
                  <div>
                    <span>综合</span>
                    <strong>{analysis.overall_score}</strong>
                  </div>
                  <div>
                    <span>学业</span>
                    <strong>{analysis.academic_score}</strong>
                  </div>
                  <div>
                    <span>科研</span>
                    <strong>{analysis.research_score}</strong>
                  </div>
                  <div>
                    <span>项目</span>
                    <strong>{analysis.project_score}</strong>
                  </div>
                </div>
                <p className="summaryText">{analysis.summary}</p>
                <div className="contentGrid">
                  <div className="panel insetPanel">
                    <h4>优势</h4>
                    <ul className="plainList">
                      {analysis.strengths.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="panel insetPanel">
                    <h4>待补强</h4>
                    <ul className="plainList">
                      {analysis.weaknesses.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
                <div className="panel insetPanel">
                  <h4>下一步建议</h4>
                  <ul className="plainList">
                    {analysis.suggestions.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </>
            ) : (
              <p className="emptyText">点击“分析背景”后，这里会展示你的优势、短板和准备建议。</p>
            )}
          </div>
        </div>
      </div>
    </Section>
  );
}
