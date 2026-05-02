"""使用指南 / 사용 가이드 — 자문가용 상세 매뉴얼 (中文 우선, CWA 段位制 기반)."""
import textwrap

import streamlit as st

from _ui import hero
from core.i18n import t, current_lang


def _md(html: str) -> None:
    """Render HTML safely — strips indentation so Streamlit markdown doesn't treat it as a code block."""
    st.markdown(textwrap.dedent(html).strip(), unsafe_allow_html=True)


CALLOUT_CSS = """
<style>
  .guide-section {
    background: #FFFFFF;
    border: 1px solid #ECE5DC;
    border-radius: 14px;
    padding: 22px 26px;
    margin-bottom: 18px;
  }
  .guide-section h3 {
    margin: 0 0 14px 0;
    color: #1F1B16;
    font-size: 19px;
    border-bottom: 2px solid #C0392B;
    padding-bottom: 8px;
    display: inline-block;
  }
  .guide-tip {
    background: #FFF8EC;
    border-left: 4px solid #C97A1B;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 12px 0;
    font-size: 14px;
  }
  .guide-warn {
    background: #FDF1EF;
    border-left: 4px solid #B0392B;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 12px 0;
    font-size: 14px;
  }
  .guide-info {
    background: #EDF3FB;
    border-left: 4px solid #2D5BAD;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 12px 0;
    font-size: 14px;
  }
  .guide-step {
    display: flex;
    gap: 14px;
    align-items: flex-start;
    padding: 10px 0;
  }
  .guide-step-num {
    background: #C0392B;
    color: white;
    border-radius: 50%;
    width: 26px;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    flex-shrink: 0;
    font-size: 13px;
  }
  .guide-table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    font-size: 14px;
  }
  .guide-table th {
    background: #FAF7F2;
    text-align: left;
    padding: 10px 12px;
    border-bottom: 2px solid #ECE5DC;
    font-weight: 600;
  }
  .guide-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #F2EDE5;
    vertical-align: top;
  }
  .kbd {
    background: #F4EFE7;
    border: 1px solid #D9CFC2;
    border-radius: 4px;
    padding: 2px 6px;
    font-family: monospace;
    font-size: 12px;
  }
</style>
"""


def _section(title: str, body_html: str) -> None:
    body = textwrap.dedent(body_html).strip()
    _md(f'<div class="guide-section"><h3>{title}</h3>{body}</div>')


def _zh_guide() -> None:
    """详细中文指引 — 给国家武术队顾问的完整说明."""
    st.markdown(CALLOUT_CSS, unsafe_allow_html=True)

    _md("""
        <div class="guide-warn" style="border-left-color:#C97A1B;background:#FFF4E0">
        <b>🔧 这是开发阶段的内部工具</b> — 不是给学员使用的最终产品。
        学员将通过将来的移动应用使用本系统。
        您在此提供的示范视频、意见、判定都会成为最终应用的基础。
        </div>
    """)

    _section(
        "1. 评估标准:中国武术段位制",
        """
        <p>本系统按 <b>中国武术协会 (CWA) 段位制</b>(高等教育出版社《系列教程》)
        评估学员套路。<b>不</b> 采用国际武联 (IWUF) 竞赛规则 —
        段位制针对学员考试,IWUF 针对竞赛,两者不同。</p>
        <p>您的示范视频成为 AI 学习的标准,您的判定数据成为 AI 调整的依据。
        AI 只知道"和您的示范有多接近",所以您的示范质量直接决定系统质量。</p>
        """,
    )

    _section(
        "2. 系统怎么工作?",
        """
        <p>摄像头视频 → AI 提取 33 个关键点 → 计算关节角度
        → 与您示范视频逐帧比对 → 综合得分 + 偏差点。</p>
        """,
    )

    _section(
        "3. 工作台已经为您准备好了什么?",
        """
        <p>开发者(我)和 AI 已经做了以下准备工作,这样您不用从零开始:</p>

        <div class="guide-step">
          <div class="guide-step-num">A</div>
          <div><b>套路目录已就位</b><br/>
          系统预置了 <b>10 个 CWA 段位制 套路</b>:<br/>
          • 长拳 一段 / 二段 / 三段(单练套路,有完整动作序列)<br/>
          • 剑术 一段 / 二段 / 三段(教程存在,动作细节需您补充)<br/>
          • 短棍 一段 / 二段 / 三段(教程存在,动作细节需您补充)<br/>
          • 24 式简化太极拳(1956 国家体委,非段位制但是基础入门)
          </div>
        </div>

        <div class="guide-step">
          <div class="guide-step-num">B</div>
          <div><b>每个套路的 AI 指引已自动生成</b><br/>
          每个套路页面顶部有「📋 AI 整理的指引」面板,内容来自:<br/>
          • 高等教育出版社《中国武术段位制系列教程》(官方)<br/>
          • 国家体育总局官方文件<br/>
          所有信息都标注了来源 URL,您可以直接点击核对。
          </div>
        </div>

        <div class="guide-step">
          <div class="guide-step-num">C</div>
          <div><b>已核实的事实 vs 待补充的项目分开标注</b><br/>
          ✅ 绿色标记 = 已核实(从官方教程引用)<br/>
          ⚠️ 黄色标记 = 待您补充(AI 没有可靠来源,需要您的专业判断)
          </div>
        </div>

        <div class="guide-warn">
          <b>⚠️ 重要 — 段位制的实际范围</b><br/>
          段位制官方教程中,<b>"刀术 / 长棍 / 枪术"作为独立段位套路并不存在</b>。
          这些武器在长拳类教程或国家体委 1989 年的国际竞赛规定套路里出现,但不属于段位制。
          所以系统目前只列出段位制实际有的:长拳、剑术、短棍(短棍而非长棍)、加上 24 式。
          如果您觉得需要其他套路,请在「您的意见」中告诉开发者。
        </div>
        """,
    )

    _section(
        "4. 您的工作流程 — 三步",
        """
        <div class="guide-step">
          <div class="guide-step-num">A</div>
          <div><b>检查 AI 指引</b>(在每个套路页面)<br/>
          打开「📋 AI 整理的指引」 — 看看 AI 列的事实是否正确。
          有错误或需要补充的,直接在「✏️ 您的意见」文本框里写下来。
          您写中文,系统自动翻译成韩文给开发者。</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">B</div>
          <div><b>录制并上传标准动作</b><br/>
          按照拍摄要求(下面有详细)录制您本人示范的套路视频,上传到「标准动作」页面。
          建议每个套路录 <b>3 个镜次</b>,系统会取最优作为 AI 学习的标准。</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">C</div>
          <div><b>测试 AI 反应</b>(在「测试」页面)<br/>
          您再录一段视频 — 比如故意把马步膝盖弯到 75°(本来应该 90°),
          看 AI 能不能识别出这个错误。然后告诉系统:✓ 识别正确 / ✗ 漏检了 / ✗ 误判了。</div>
        </div>
        """,
    )

    _section(
        "5. 拍摄要求(很重要)",
        """
        <p>AI 准确度 90% 取决于您的拍摄质量。请尽量遵守:</p>
        <table class="guide-table">
          <tr><th>项目</th><th>建议</th></tr>
          <tr><td>角度</td><td>正面拍摄(摄像头对准您的正前方)</td></tr>
          <tr><td>距离</td><td>大约 3 米,确保全身入镜</td></tr>
          <tr><td>背景</td><td>简洁,光线均匀,避免逆光、镜面、反光地板</td></tr>
          <tr><td>方向</td><td>横向拍摄(landscape),不要竖屏</td></tr>
          <tr><td>分辨率</td><td>720p 或 1080p,30fps</td></tr>
          <tr><td>时长</td><td>从起势到收势的完整套路,中间不要停或剪辑</td></tr>
        </table>

        <div class="guide-warn">
          <b>⚠️ 如果骨架明显错位</b>(左右反、关节飞出体外、整段没识别到人):
          删掉重拍。错误数据会让 AI 学坏。
        </div>
        """,
    )

    _section(
        "6. 标准动作页面 — 详细使用",
        """
        <div class="guide-step">
          <div class="guide-step-num">1</div>
          <div>选择套路(例如「长拳 一段」)</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">2</div>
          <div>展开「📋 AI 整理的指引」 — 阅读、检查、有意见就在「✏️ 您的意见」里写</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">3</div>
          <div>滚动到「上传新镜次」,选择您拍好的视频文件上传</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">4</div>
          <div>调整「自我评分」滑块(100 = 完美示范, 80 = 一般训练, 60 = 状态不好)。
          系统会用这个分数挑选最佳镜次作为标准。</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">5</div>
          <div>点击「提取姿势并保存」 — 大约 30 秒到 1 分钟完成</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">6</div>
          <div>检查骨架预览,确认 AI 正确识别了您的身体。如果有明显错误,删除并重拍</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">7</div>
          <div>录够 1 个就可以激活套路;录 3 个以上会让 AI 学到您动作的自然变化范围</div>
        </div>
        """,
    )

    _section(
        "7. 测试页面 — 详细使用",
        """
        <p>这个页面是您 <b>调试 AI</b> 的地方。
        您扮演"出题人":提供变化视频,看 AI 答得对不对。</p>

        <h4>什么时候用?</h4>
        <ul>
          <li>录完标准动作后,验证 AI 对标准情况能给高分</li>
          <li>故意做错某个动作,看 AI 能不能识别错误</li>
          <li>给开发者提供"AI 还有哪些不会"的具体证据</li>
        </ul>

        <h4 style="margin-top:14px">操作步骤</h4>
        <div class="guide-step">
          <div class="guide-step-num">1</div>
          <div>选择已激活的套路</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">2</div>
          <div>上传测试视频 + 写明意图(例如「马步膝盖故意弯到 75°」)</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">3</div>
          <div>选「期望结果」:AI 应识别 / 应忽略 / 任意</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">4</div>
          <div>点「执行评分」,系统给出评分 + 检出的问题</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">5</div>
          <div>给出判定 — <b>✓ 正确识别</b> / <b>✗ 漏检</b> / <b>✗ 误判</b></div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">6</div>
          <div>(可选)展开「添加评论」写更详细的中文说明</div>
        </div>
        """,
    )

    _section(
        "8. 您的总体意见 (在主页) — 重要",
        """
        <p>不只是某个套路的问题。<b>对整个系统的任何想法</b> —
        UI、产品方向、评分流程、学员练习顺序、希望增加的功能、
        段位制评分的实际经验、教学方法等等 —
        都请到 <b>主页底部「💬 您的意见」</b> 框里自由地写下来。中文写就行,自动翻译。</p>

        <div class="guide-tip">
          <b>💡 写得越详细,越能精确反映</b>。
          "评分流程应该是先 ... 然后 ... 因为 ..." 比 "评分流程不太对" 好得多。
        </div>

        <h4 style="margin-top:14px">两个意见框的区别</h4>
        <table class="guide-table">
          <tr><th>位置</th><th>写什么</th></tr>
          <tr>
            <td><b>套路页面</b> · <span class="kbd">✏️ 您的意见</span></td>
            <td>该套路具体细节(动作数、步型阈值、序列等)</td>
          </tr>
          <tr>
            <td><b>主页</b> · <span class="kbd">💬 您的意见</span></td>
            <td>系统层面(UI、流程、新功能、教学经验、对整体的想法)</td>
          </tr>
        </table>
        """,
    )

    _section(
        "9. 我应该怎么开始?",
        """
        <ol>
          <li>「套路管理」中选择您最熟悉的套路(建议「长拳 一段」)</li>
          <li>「标准动作」页选这个套路 → 检查 AI 指引 → 有意见就写下来</li>
          <li>手机正面拍摄 → 上传 → 自我评分 → 保存</li>
          <li>再录 2 个镜次后激活 → 在「测试」上传标准+变化视频 → 评分 → 判定</li>
        </ol>

        <div class="guide-tip">
          <b>💡 节奏</b>:每周 30~60 分钟即可,不需要一次做完。
        </div>
        """,
    )

    _section(
        "10. 遇到问题怎么办?",
        """
        <ul>
          <li><b>页面打不开</b>:告诉开发者</li>
          <li><b>视频上传失败</b>:用 mp4,大小 500MB 以内</li>
          <li><b>骨架明显不对</b>:删掉重拍</li>
          <li><b>AI 评分明显不合理</b>:在测试页面按「AI 误判」并写评论</li>
          <li><b>套路目录缺某套路</b>:「✏️ 您的意见」里写明,或在「套路管理」自己添加</li>
        </ul>
        """,
    )


def _ko_guide() -> None:
    """한국어 상세 가이드 — _zh_guide와 동일한 구조·깊이. 본인이 자문가가 보는 내용을 1:1로 확인 가능."""
    st.markdown(CALLOUT_CSS, unsafe_allow_html=True)

    _md("""
        <div class="guide-info" style="font-size:13px;padding:10px 14px">
        💡 中文로 보려면 좌측 상단 <b>🇨🇳 中文</b> 토글.
        </div>
    """)

    # 최상단 — 개발 단계 도구 안내
    _md("""
        <div class="guide-warn" style="border-left-color:#C97A1B;background:#FFF4E0">
        <b>🔧 먼저 알려드립니다 — 이건 개발 단계의 내부 도구입니다</b><br/><br/>
        본 워크벤치는 학생용 최종 제품이 <b>아닙니다</b>.
        <b>모바일 앱 출시 전, AI를 학습·튜닝하기 위한 내부 도구</b>입니다.<br/><br/>
        학생들은 추후 <b>모바일 앱</b>을 통해 시스템을 사용하게 됩니다.
        여기서 자문가가 제공한 시범 영상·의견·판정은 모두 최종 앱의 기반이 됩니다.<br/><br/>
        <i>그래서 이 곳을 "AI 교습 워크벤치"로 봐주시면 됩니다 —
        자문가가 선생님, AI가 학생, 함께 AI를 잘 가르쳐서 미래에 학생들에게 도움 되도록.</i>
        </div>
    """)

    _section(
        "1. 평가 기준: 中国武术段位制",
        """
        <p>본 시스템은 <b>中国武术协会 (CWA) 段位制</b>(高等教育出版社《系列教程》) 기준으로
        학생 套路를 평가합니다. <b>국제 무술 연맹 (IWUF) 시합 규정은 사용하지 않음</b> —
        段位制는 학생 단증용, IWUF는 시합용으로 다른 시스템.</p>
        <p>자문가 시범 영상이 AI 학습의 표준, 판정 데이터가 AI 조정의 근거가 됩니다.
        AI는 "자문가 시범과 얼마나 비슷한지"만 알기에, 시범 품질이 시스템 품질을 좌우.</p>
        """,
    )

    _section(
        "2. 시스템 작동",
        """
        <p>카메라 영상 → AI가 33개 키포인트 추출 → 관절 각도 계산
        → 자문가 시범 영상과 프레임별 비교 → 점수 + 편차 항목.</p>
        """,
    )

    _section(
        "3. 워크벤치가 미리 준비해둔 것",
        """
        <p>개발자(본인)와 AI가 미리 다음을 준비해뒀어요. 자문가가 맨땅에서 시작하지 않도록:</p>

        <div class="guide-step">
          <div class="guide-step-num">A</div>
          <div><b>폼 카탈로그가 이미 들어가 있음</b><br/>
          <b>10개의 CWA 段位制 套路</b>가 사전 등록됨:<br/>
          • 长拳 1단 / 2단 / 3단 (단련套路, 동작 시퀀스 완전 검증)<br/>
          • 剑术 1단 / 2단 / 3단 (교본 ISBN 확인, 동작 세부는 자문가 보완)<br/>
          • 短棍 1단 / 2단 / 3단 (교본 존재, 세부 자문가 보완)<br/>
          • 24式 简化太极拳 (1956 国家体委, 段位制 아님이지만 입문 기초)
          </div>
        </div>

        <div class="guide-step">
          <div class="guide-step-num">B</div>
          <div><b>각 폼별 AI 가이드라인이 자동 생성됨</b><br/>
          각 폼 페이지 상단에 「📋 AI 가이드라인」 패널이 있음. 출처:<br/>
          • 高等교육出版社《中国武术段位制系列교程》(공식)<br/>
          • 国家体育总局 공식 문서<br/>
          모든 정보에 출처 URL 표시, 자문가가 직접 클릭해서 확인 가능.
          </div>
        </div>

        <div class="guide-step">
          <div class="guide-step-num">C</div>
          <div><b>검증된 사실 vs 보완 필요 항목 분리 표시</b><br/>
          ✅ 녹색 = 공식 교본에서 인용된 검증된 사실<br/>
          ⚠️ 노랑 = 자문가 보완 필요 (AI가 신뢰할 출처 못 찾음, 전문 판단 필요)
          </div>
        </div>

        <div class="guide-warn">
          <b>⚠️ 중요 — 段位制의 실제 범위</b><br/>
          段位制 公式 教程에서 <b>"도술 / 장곤 / 창술" standalone 套路는 존재하지 않습니다</b>.
          이런 무기는 长拳 계열 교본 안에 또는 1989년 国家体委 国際规정套路 (시합용)에 있고,
          段位制와는 별개. 그래서 시스템은 段位制에 실제 있는 것만 표시 —
          长拳·剑術·短棍(장곤 아닌 단봉)·24식. 다른 套路 필요하시면 「자문가 의견」에서 알려주시면 됨.
        </div>
        """,
    )

    _section(
        "4. 자문가 워크플로 — 3단계",
        """
        <div class="guide-step">
          <div class="guide-step-num">A</div>
          <div><b>AI 가이드라인 검토</b> (각 폼 페이지)<br/>
          「📋 AI 가이드라인」 펼치기 → AI가 적은 사실이 정확한지 확인.
          틀리거나 보완할 게 있으면 바로 「✏️ 자문가 의견」 텍스트박스에 적기.
          中文로 적으면 자동으로 한국어 번역되어 개발자에게 전달.</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">B</div>
          <div><b>시범 영상 녹화 및 등록</b><br/>
          촬영 요건(아래 자세히 설명)에 따라 자문가 시범 영상 녹화 후 「시범 영상」 페이지에 업로드.
          폼당 <b>3 테이크</b> 권장, 시스템이 최적을 골라 AI 학습 표준으로 사용.</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">C</div>
          <div><b>AI 반응 테스트</b> (「AI 테스트」 페이지)<br/>
          변형 영상을 또 찍어서 — 예) 일부러 마보 무릎을 75°로 굽혀서 (정상은 90°) — AI가 인식하는지.
          그 후 ✓ 맞게 잡음 / ✗ 놓침 / ✗ 오탐 판정.</div>
        </div>
        """,
    )

    _section(
        "5. 촬영 요건 (매우 중요)",
        """
        <p>AI 정확도의 90%는 자문가 촬영 품질에서 결정됩니다. 가능한 한 지켜주세요:</p>
        <table class="guide-table">
          <tr><th>항목</th><th>권장</th></tr>
          <tr><td>각도</td><td>정면 촬영 (카메라가 자문가 정면)</td></tr>
          <tr><td>거리</td><td>약 3m, 전신이 화면에 들어오게</td></tr>
          <tr><td>배경</td><td>단순, 균일한 조명, 역광·거울·반사 바닥 피하기</td></tr>
          <tr><td>방향</td><td>횡촬 (landscape), 세로 촬영 X</td></tr>
          <tr><td>해상도</td><td>720p 또는 1080p, 30fps</td></tr>
          <tr><td>시간</td><td>기세부터 수세까지 한 컷, 중간 정지·편집 X</td></tr>
        </table>

        <div class="guide-warn">
          <b>⚠️ 골격이 명백히 틀리게 잡히면</b> (좌우 반전 / 관절이 몸 밖으로 / 영상 내내 사람 인식 안 됨):
          삭제하고 재촬영. 잘못된 데이터가 들어가면 AI가 잘못 학습합니다.
        </div>
        """,
    )

    _section(
        "6. 「시범 영상」 페이지 — 자세한 사용법",
        """
        <div class="guide-step">
          <div class="guide-step-num">1</div>
          <div>폼 선택 (예: 「장권 1단」)</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">2</div>
          <div>「📋 AI 가이드라인」 펼치기 → 읽고 검토 → 의견 있으면 「✏️ 자문가 의견」에 적기</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">3</div>
          <div>「새 시범 올리기」로 스크롤, 촬영한 영상 파일 선택해서 업로드</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">4</div>
          <div>「자기평가」 슬라이더 조정 (100 = 완벽한 시범, 80 = 일반 컨디션, 60 = 좋지 않음).
          시스템이 이 점수로 최적 테이크를 골라 표준으로 삼음.</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">5</div>
          <div>「자세 추출 및 저장」 클릭 — 약 30초~1분 소요</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">6</div>
          <div>골격 미리보기 확인, AI가 자문가 신체를 정확히 인식했는지. 명백히 틀리면 삭제·재촬영</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">7</div>
          <div>1개만 있어도 활성화 가능, 3개 이상 권장 (자연스러운 변동 범위 학습)</div>
        </div>
        """,
    )

    _section(
        "7. 「AI 테스트」 페이지 — 자세한 사용법",
        """
        <p>이 페이지는 자문가가 <b>AI를 디버깅</b>하는 곳.
        자문가가 "출제자" 역할 — 변형 영상 제공, AI가 맞게 답하는지 확인.</p>

        <h4>언제 사용?</h4>
        <ul>
          <li>표준 동작 등록 후, AI가 표준 케이스에 높은 점수 주는지 확인</li>
          <li>일부러 잘못된 동작 → AI가 오류 잡아내는지</li>
          <li>"AI가 아직 못 하는 게 무엇인지" 개발자에게 구체 증거 제공</li>
        </ul>

        <h4 style="margin-top:14px">조작 단계</h4>
        <div class="guide-step">
          <div class="guide-step-num">1</div>
          <div>활성화된 폼 선택</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">2</div>
          <div>테스트 영상 업로드 + 의도 적기 (예: "마보 무릎을 일부러 75°로 굽힘")</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">3</div>
          <div>「기대 결과」 선택: AI가 잡아야 함 / 무시해야 함 / 무엇이든</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">4</div>
          <div>「채점 실행」 클릭, 시스템이 점수 + 검출 문제 표시</div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">5</div>
          <div>판정 — <b>✓ 맞게 잡음</b> / <b>✗ 놓침</b> / <b>✗ 오탐</b></div>
        </div>
        <div class="guide-step">
          <div class="guide-step-num">6</div>
          <div>(선택) 「코멘트 추가」 펼쳐서 中文로 더 자세히 설명</div>
        </div>
        """,
    )

    _section(
        "8. 자문가 종합 의견 (홈 화면) — 중요",
        """
        <p>특정 폼 문제만이 아니라 <b>시스템 전반에 대한 어떤 생각이든</b> —
        UI · 제품 방향 · 평가 흐름 · 학생 연습 순서 · 추가 기능 ·
        段位制 채점 실제 경험 · 교수법 등 무엇이든 —
        <b>홈 화면 맨 아래 「💬 자문가 의견」</b> 박스에 자유롭게. 中文 입력 가능, 자동 번역.</p>

        <div class="guide-tip">
          <b>💡 자세할수록 정확하게 반영됩니다</b>.
          "채점 흐름은 먼저 ... 그다음 ... 왜냐면 ..." 이 "채점 흐름이 좀 이상함"보다 훨씬 가치 있음.
        </div>

        <h4 style="margin-top:14px">두 의견 박스의 차이</h4>
        <table class="guide-table">
          <tr><th>위치</th><th>무엇을 적나</th></tr>
          <tr>
            <td><b>폼 페이지</b> · <span class="kbd">✏️ 자문가 의견</span></td>
            <td>그 폼의 구체적 디테일 (동작 수, 보형 임계값, 시퀀스 등)</td>
          </tr>
          <tr>
            <td><b>홈 화면</b> · <span class="kbd">💬 자문가 의견</span></td>
            <td>시스템 차원 (UI, 흐름, 새 기능, 교수 경험, 전반에 대한 생각)</td>
          </tr>
        </table>
        """,
    )

    _section(
        "9. 어떻게 시작할까?",
        """
        <ol>
          <li>「품세 관리」에서 가장 익숙한 폼 선택 (권장:「장권 1단」)</li>
          <li>「시범 영상」 페이지에서 그 폼 선택 → AI 가이드 검토 → 의견 있으면 적기</li>
          <li>핸드폰으로 정면 촬영 → 업로드 → 자기평가 → 저장</li>
          <li>2 테이크 더 추가 후 활성화 → 「AI 테스트」에서 표준·변형 영상 채점 → 판정</li>
        </ol>

        <div class="guide-tip">
          <b>💡 페이스</b>: 매주 30~60분이면 충분. 한 번에 다 할 필요 없음.
        </div>
        """,
    )

    _section(
        "10. 문제 발생 시 대처",
        """
        <ul>
          <li><b>페이지 안 열림</b>: 개발자에게 알리기</li>
          <li><b>영상 업로드 실패</b>: mp4 사용, 500MB 이내</li>
          <li><b>골격이 명백히 틀림</b>: 삭제하고 재촬영</li>
          <li><b>AI 점수가 명백히 부적절</b>: AI 테스트에서 「AI 오탐」 누르고 코멘트 작성</li>
          <li><b>품세 카탈로그에 원하는 폼이 없음</b>: 「✏️ 자문가 의견」에 적거나 「품세 관리」에서 직접 추가</li>
        </ul>
        """,
    )


def render() -> None:
    is_zh = current_lang() == "zh"
    hero(
        title="使用指南" if is_zh else "사용 가이드",
        subtitle="武术 AI 评分工作台 — 给国家武术队顾问的完整说明" if is_zh else
                 "우슈 AI 평가 워크벤치 — 자문가용 상세 매뉴얼 (한국어 동일 버전)",
    )

    if is_zh:
        _zh_guide()
    else:
        _ko_guide()
