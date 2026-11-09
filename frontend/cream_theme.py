"""Light, warm Norunja presentation theme. No engine/data dependencies.

Design goal: a calm ivory canvas, white cards, soft yolk-yellow highlights,
charcoal text, and one restrained dark explainer card. Original themes remain
available without any changes to the model's output.
"""

CREAM_CSS = r"""
<style>
:root {
  --nj-canvas:#F9F9F5;
  --nj-sidebar:#FFFEFB;
  --nj-paper:#FFFFFF;
  --nj-cream:#FFF2CD;
  --nj-cream-edge:#F2DEA2;
  --nj-gold:#F8CB52;
  --nj-gold-strong:#E9AA19;
  --nj-gold-wash:#FFF6DD;
  --nj-ink:#26313A;
  --nj-heading:#26313A;
  --nj-muted:#69737B;
  --nj-border:#EAE9E2;
  --nj-navy:#222C38;
  --nj-green:#237C69;
}
/* Layout and background */
html, body, .stApp, [data-testid='stApp'],
[data-testid='stAppViewContainer'],
[data-testid='stMain'], main,
[data-testid='stMainBlockContainer'] {
  background:var(--nj-canvas) !important;
  color:var(--nj-ink) !important;
}
[data-testid='stHeader'] {background:transparent !important;}
[data-testid='stBottomBlockContainer'] {background:var(--nj-canvas) !important;}
[data-testid='stMainBlockContainer'],section.main .block-container{
  max-width:1360px !important;padding:2.0rem 2.9rem 5rem !important;
}
[data-testid='stSidebar'], section[data-testid='stSidebar']{
  background:var(--nj-sidebar) !important;
  border-right:1px solid #ECEBE4 !important;
}
[data-testid='stSidebar'] .block-container,
[data-testid='stSidebarContent'] {background:var(--nj-sidebar) !important;}
[data-testid='stSidebar'] .block-container {padding:1.85rem 1rem !important;}
[data-testid='stSidebar'] [data-testid='stMarkdownContainer'] p,
[data-testid='stSidebar'] label,
[data-testid='stSidebar'] span,
[data-testid='stSidebar'] [data-testid='stCaptionContainer']{
  color:var(--nj-ink);
}
/* Base typography */
body, input, textarea, button, p, label, small, li, blockquote,
[data-testid='stMarkdownContainer'], [data-testid='stWidgetLabel'] p {
  font-family:'Pretendard','Noto Sans KR','Malgun Gothic',system-ui,sans-serif;
}
[data-testid='stMarkdownContainer'] p,
[data-testid='stMarkdownContainer'] li,
[data-testid='stText'], .stCaption, .stMarkdown {
  color:var(--nj-ink);
}
[data-testid='stCaptionContainer'] p, [data-testid='stCaptionContainer'] span,
small, .stCaption {color:var(--nj-muted) !important;}
[data-testid='stWidgetLabel'] p {color:#3E454A !important;font-size:.88rem;font-weight:730;}
h1,h2,h3,h4,h5 {color:var(--nj-ink)!important;letter-spacing:-.04em;}
/* Input surfaces: readable labels, not dark-on-dark */
[data-testid='stTextArea'] textarea,
[data-testid='stTextInput'] input,
[data-testid='stNumberInput'] input,
[data-testid='stTimeInput'] input,
[data-testid='stSelectbox'] div[data-baseweb='select']>div,
[data-testid='stMultiSelect'] div[data-baseweb='select']>div,
[data-testid='stDateInput'] input,
[data-testid='stFileUploader'] section {
  background:#FFFFFF!important;color:var(--nj-ink)!important;
  border:1px solid #E3E6E6!important;border-radius:10px!important;
  box-shadow:0 1px 2px rgba(30,35,38,.025)!important;
}
[data-testid='stTextArea'] textarea {font-size:1rem!important;line-height:1.65!important;}
[data-testid='stTextArea'] textarea:focus,
[data-testid='stTextInput'] input:focus,
[data-testid='stNumberInput'] input:focus,
[data-testid='stTimeInput'] input:focus{
  border-color:#E6B641!important;box-shadow:0 0 0 2px #F8CB5240!important;
}
[data-testid='stTextArea'] textarea::placeholder,
[data-testid='stTextInput'] input::placeholder {color:#A1A7A8!important;}
[data-testid='stNumberInput'] button,
[data-testid='stTimeInput'] button {background:#FFF!important;color:#525D64!important;border-color:#E7E8E8!important;}
[data-baseweb='select'] input, [data-baseweb='select'] span,
[data-baseweb='select'] div, [data-baseweb='select'] svg {
  color:var(--nj-ink);
}
[data-baseweb='select'] svg {fill:#5D6972!important;}
[data-baseweb='tag'] {background:#FFF1C9!important;border:1px solid #EACD72!important;}
[data-baseweb='tag'] span {color:#65501F!important;}
[data-testid='stRadio'] label, [data-testid='stCheckbox'] label {color:#35414A!important;}
/* Buttons */
.stButton>button {
  background:#FFFFFF!important;border:1px solid #E4E5E2!important;
  color:var(--nj-ink)!important;border-radius:11px!important;
  min-height:42px;font-size:.92rem;font-weight:730;
  transition:all .15s ease;
}
.stButton>button:hover {background:#FFF8E4!important;border-color:#E6C465!important;}
.stButton>button[kind='primary'],
.stButton>button[data-testid='stBaseButton-primary'] {
  background:#F6C84D!important;color:#3D3219!important;
  border-color:#F6C84D!important;box-shadow:0 3px 8px #CBAB5A24;
}
.stButton>button[kind='primary']:hover {background:#FBE091!important;}
[data-testid='stDownloadButton'] button {
  color:#52616B!important;background:#FFF!important;border:1px solid #E5E5E0!important;
  border-radius:10px!important;font-weight:650;
}
[data-testid='stDownloadButton'] button:hover {border-color:#E4BA4C!important;background:#FFF8E5!important;}
/* Cards, tabs, expanders, separators */
[data-testid='stVerticalBlockBorderWrapper']>div,
[data-testid='stVerticalBlockBorderWrapper']>[data-testid='stVerticalBlock'] {
  background:#FFFFFF;border-color:var(--nj-border)!important;
  border-radius:17px;
}
[data-testid='stExpander'] {
  background:#FFFFFF!important;border:1px solid var(--nj-border)!important;
  border-radius:15px!important;box-shadow:0 2px 9px #35414A06;
}
[data-testid='stExpander'] summary, [data-testid='stExpander'] p {color:var(--nj-ink)!important;}
[data-testid='stAlert'] {border-radius:11px!important;}
[data-testid='stMetric'] {
  background:#FFF!important;border:1px solid var(--nj-border)!important;
  border-radius:14px;padding:15px;
}
[data-testid='stMetricLabel'] p {color:var(--nj-muted)!important;font-size:.88rem;}
[data-testid='stMetricValue'] {color:var(--nj-ink)!important;font-size:1.55rem!important;}
[data-testid='stDataFrame'] {border:1px solid var(--nj-border);border-radius:13px;overflow:hidden;}
[data-testid='stTabs']{margin-top:16px;}
[data-testid='stTabs'] [data-baseweb='tab-list']{
  background:#FFFFFF;border:1px solid #EEEDE8;border-radius:14px;
  padding:5px;gap:5px;box-shadow:0 2px 10px #27333E07;
}
[data-testid='stTabs'] button[role='tab']{
  background:transparent;color:#777E84!important;border-radius:9px;
  font-weight:700;line-height:1.2;padding:12px 13px;
}
[data-testid='stTabs'] button[aria-selected='true']{
  color:#3F3525!important;background:#FFF1C5!important;
}
[data-testid='stTabs'] [data-baseweb='tab-highlight']{background:transparent!important;}
[data-testid='stTabs'] [data-baseweb='tab-border']{display:none!important;}
hr {border-color:#EAE9E3!important;}
header#streamlitHeader,footer {visibility:hidden;}
/* Design-specific text and section components */
.ls-side-name {font-size:1.25rem!important;font-weight:900;color:#26323A!important;letter-spacing:-.06em;}
.ls-side-sub {color:#98A0A2!important;font-size:.71rem!important;margin-top:3px;margin-bottom:18px;}
.ls-file {color:#68747A!important;font-size:.80rem;line-height:2.1;}
.ls-dot {background:#EFBF45!important;}
.ls-dot.missing {background:#BFC6C5!important;}
.ls-kicker {font-size:.7rem;color:#AA8026!important;font-weight:850;letter-spacing:.16em;margin-bottom:9px;}
.ls-head {display:flex;gap:12px;align-items:center;margin-bottom:7px;}
.ls-mark {width:45px;height:45px;display:flex;align-items:center;justify-content:center;
  background:#FFE39A;border-radius:13px;color:#8C6C17;font-size:23px;font-weight:900;box-shadow:none;}
.ls-title {font-size:2.4rem;font-weight:900;color:var(--nj-ink)!important;letter-spacing:-.07em;}
.ls-sub {color:#687680!important;line-height:1.62;max-width:750px;margin:4px 0 13px;font-size:.97rem;}
.ls-pill {border:1px solid #EADAAF;padding:5px 10px;color:#876A28;background:#FFF5D8;border-radius:999px;font-size:.75rem;font-weight:750;margin-right:7px;}
.ls-pill.warn {background:#F6F5EF;border-color:#E8E6DC;color:#7C817C;}
.ls-section {display:flex;align-items:center;gap:11px;color:var(--nj-ink)!important;
  font-size:1.26rem;letter-spacing:-.045em;font-weight:850;margin:31px 0 9px;}
.ls-number {color:#B68A27!important;font-size:.76rem;font-weight:900;letter-spacing:.13em;}
.ls-copy {color:#7B8388!important;font-size:.9rem;line-height:1.62;margin-bottom:15px;}
.ls-card {background:#FFFFFF!important;border:1px solid #EBEBE6!important;
  border-radius:15px!important;min-height:131px;padding:19px 20px;
  box-shadow:0 3px 14px #34404B0A;
}
.ls-card.best {background:#FFF9E9!important;border-color:#F3D684!important;box-shadow:0 4px 16px #C7AA4F12;}
.ls-kpi-label {font-size:.81rem;color:#7E8587!important;margin-bottom:11px;font-weight:750;}
.ls-kpi-value {font-size:1.77rem;font-weight:900;color:#303B43!important;letter-spacing:-.055em;line-height:1.24;}
.ls-kpi-detail {font-size:.78rem;color:#8C9497!important;margin-top:10px;line-height:1.48;}
.ls-note {background:#FFF!important;border:1px solid #E7E8E3!important;border-radius:12px;
  color:#606E75!important;line-height:1.65;font-size:.86rem;padding:13px 16px;}
.ls-note.orange {background:#FFF9E7!important;border-color:#F0D990!important;color:#836528!important;}
.ls-diagnosis {padding:15px 17px;border-radius:12px;border:1px solid #EAE8E0;
  border-left:3px solid #EAB94B;background:#FFF!important;margin:11px 0;}
.ls-diagnosis .title {color:#303841!important;font-weight:780;}
.ls-diagnosis .detail {color:#778185!important;line-height:1.7;}
.ls-meta, .ls-footer {color:#859094!important;font-size:.81rem;line-height:1.75;}
/* Reference-inspired hero: warm yellow field with a restrained yolk illustration */
.nj-hero {
  display:flex;align-items:center;justify-content:space-between;gap:24px;
  background:linear-gradient(120deg,#FFF1C9 0%,#FFF3D2 61%,#FFEAB0 100%);
  border:1px solid #F4E4BD;border-radius:21px;
  min-height:222px;padding:35px 45px;overflow:hidden;position:relative;
  box-shadow:0 8px 22px #B9A47A0B;margin:12px 0 22px;
}
.nj-hero .nj-hero-body {position:relative;z-index:1;max-width:700px;}
.nj-hero .nj-hero-kicker {font-size:.70rem;font-weight:900;letter-spacing:.18em;color:#AB8634;margin-bottom:17px;}
.nj-hero h1 {margin:0 0 12px!important;color:#2C3539!important;font-size:2.45rem;line-height:1.25;letter-spacing:-.072em;font-weight:900;}
.nj-hero p {margin:0 0 16px!important;color:#687065!important;font-size:.95rem;line-height:1.68;}
.nj-hero .nj-pill {display:inline-block;background:#FFF9EB;border:1px solid #F4E1AF;
  color:#89702E;border-radius:999px;padding:5px 10px;font-size:.72rem;font-weight:750;margin-right:6px;margin-top:3px;}
.nj-hero-egg {position:relative;flex:0 0 205px;height:180px;display:flex;align-items:center;justify-content:center;}
.nj-hero-ring {position:absolute;border-radius:50%;width:172px;height:172px;border:13px solid #F8CE59;opacity:.72;}
.nj-hero-ring.two {width:133px;height:133px;border-width:14px;border-color:#FFE6A1;opacity:1;}
.nj-hero-yolk {position:relative;background:linear-gradient(145deg,#FFD968,#F7C13E);
  height:104px;width:104px;border-radius:50%;box-shadow:inset -8px -8px 0 #EDAF2C30, 0 12px 20px #B58C3515;}
.nj-hero-yolk::before {content:'';position:absolute;top:26px;left:28px;width:36px;height:15px;
  background:#FFF2BB;border-radius:50%;transform:rotate(-27deg);opacity:.85;}
.nj-hero-yolk::after {content:'';position:absolute;top:45px;left:59px;width:9px;height:9px;
  background:#FFF7DB;border-radius:50%;opacity:.85;}
.nj-overview {display:flex;gap:13px;align-items:flex-start;background:#252F3B;color:#FAFAF5;
  border-radius:16px;padding:20px 23px;border:1px solid #354352;min-height:138px;margin-bottom:15px;}
.nj-overview .nj-light {font-size:.70rem;color:#F4CB68;letter-spacing:.15em;font-weight:900;margin:0 0 9px;}
.nj-overview .nj-heading {font-size:1.10rem;color:#FFF!important;font-weight:850;line-height:1.4;margin:0 0 8px;}
.nj-overview p {color:#D6DCE1!important;font-size:.83rem;line-height:1.7;margin:0;}
.nj-mini-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;margin:17px 0 7px;}
.nj-mini {padding:16px 19px;background:#FFF;border:1px solid #EAE9E3;border-radius:13px;}
.nj-mini .nj-mini-top{font-size:.73rem;font-weight:850;color:#B1882B;margin-bottom:7px;}
.nj-mini .nj-mini-title{font-weight:850;font-size:.96rem;color:#303A42;}
.nj-mini .nj-mini-description {font-size:.78rem;color:#838D90;margin-top:6px;line-height:1.5;}
@media(max-width:1000px) {
  [data-testid='stMainBlockContainer'],section.main .block-container {padding:1.3rem 1.3rem 3rem!important;}
  .nj-hero{padding:26px;}
  .nj-hero-egg{flex-basis:145px;height:150px;transform:scale(.82);}
}
@media(max-width:760px){
  [data-testid='stMainBlockContainer'],section.main .block-container {padding:1rem .9rem 3rem!important;}
  .nj-hero{padding:27px 23px;min-height:auto;}
  .nj-hero h1 {font-size:1.75rem;}
  .nj-hero-egg {display:none;}
  .nj-mini-grid{grid-template-columns:1fr;gap:9px;}
  [data-testid='stTabs'] button[role='tab']{padding:9px 7px;font-size:.79rem;}
  .ls-card{min-height:auto;padding:16px;}
}
</style>
"""
