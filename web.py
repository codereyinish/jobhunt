from __future__ import annotations

import html
import json

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from .apply.router import apply_path, classify_url
from .core import db
from .core.config import settings
from .match.score import location_ok, score_job

app = FastAPI()

CSS = """
/* ── Design system: neutral graphite, monochrome + soft-white accents ── */
:root{
  --bg:#0a0a0b;
  --panel:#161618;
  --panel2:#1d1d20;
  --elevated:#252528;
  --line:#2b2b2f;
  --line2:#3a3a3f;
  --text:#f0f0f1;
  --muted:#b2b2ba;
  --faint:#8c8c95;
  --accent:#14d9c4;
  --accent-2:#4fe8d7;
  --accent-soft:rgba(20,217,196,.09);
  --green:#4faf78;
  --amber:#c99a4a;
  --red:#d96f6f;
  --violet:#9a91ad;
  --info:#7aa2e8;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0;
  background:var(--bg);
  color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
  font-size:15px;line-height:1.55;letter-spacing:-.004em;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;
}
::selection{background:rgba(20,217,196,.16);color:var(--text)}
code{
  background:var(--panel2);border:1px solid var(--line2);
  border-radius:4px;padding:1px 5px;
  font-family:ui-monospace,'Cascadia Code','Fira Code',monospace;
  font-size:.87em;color:var(--text);letter-spacing:0;
}
input[type=number]::-webkit-inner-spin-button,
input[type=number]::-webkit-outer-spin-button{-webkit-appearance:none;margin:0}
input[type=number]{-moz-appearance:textfield}

/* ── Layout ── */
.wrap{max-width:1160px;margin:0 auto;padding:36px 32px 100px}

/* ── Header ── */
header{
  display:flex;align-items:center;justify-content:space-between;
  padding-bottom:20px;margin-bottom:24px;
  border-bottom:1px solid var(--line);
}
.brandwrap{display:flex;flex-direction:column;gap:4px}
.brand{
  font-size:19px;font-weight:700;letter-spacing:-.02em;
  display:flex;align-items:center;gap:9px;color:var(--text);
}
.brand .dot{
  width:7px;height:7px;border-radius:50%;
  background:var(--green);flex-shrink:0;
  box-shadow:0 0 0 2px rgba(52,211,153,.15),0 0 8px rgba(52,211,153,.28);
  animation:livebeat 3.6s ease-in-out infinite;
}
@keyframes livebeat{
  0%,100%{box-shadow:0 0 0 2px rgba(52,211,153,.14),0 0 6px rgba(52,211,153,.22)}
  50%{box-shadow:0 0 0 3px rgba(52,211,153,.07),0 0 14px rgba(52,211,153,.3)}
}
.meta{color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums;letter-spacing:.003em}
.meta b{color:var(--text);font-weight:600}
a{color:var(--accent);text-decoration:none;transition:color .12s}
a:hover{color:var(--accent-2)}

/* ── Toolbar ── */
.toolbar{display:flex;gap:8px;align-items:center}
.tool-btn{
  background:transparent;border:1px solid var(--line2);border-radius:999px;
  padding:7px 14px;font-size:12.5px;font-weight:500;color:var(--muted);
  cursor:pointer;display:flex;align-items:center;gap:6px;letter-spacing:-.004em;
  transition:color .14s,border-color .14s,background .14s;
}
.tool-btn:hover{
  color:var(--text);
  border-color:rgba(20,217,196,.38);
  background:rgba(20,217,196,.04);
}
.heart-btn{
  width:37px;height:37px;border-radius:50%;
  background:transparent;border:1px solid var(--line2);
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;color:var(--faint);font-size:15px;
  transition:color .14s,border-color .14s,background .14s;
}
.heart-btn:hover{
  color:var(--red);
  border-color:rgba(248,113,113,.38);
  background:rgba(248,113,113,.055);
}

/* ── Panels ── */
.panel{
  background:var(--panel);border:1px solid var(--line);
  border-radius:14px;padding:20px 22px;margin-bottom:16px;
  box-shadow:0 2px 8px rgba(0,0,0,.22),inset 0 1px 0 rgba(255,255,255,.022);
}
.panel h2{
  font-size:10.5px;text-transform:uppercase;letter-spacing:.13em;
  color:var(--muted);margin:0 0 16px;font-weight:600;
}
details.panel>summary{
  list-style:none;cursor:pointer;user-select:none;
  font-size:10px;text-transform:uppercase;letter-spacing:.14em;
  color:var(--faint);font-weight:600;
  display:flex;align-items:center;justify-content:space-between;
}
details.panel>summary::-webkit-details-marker{display:none}
details.panel>summary::after{
  content:'';display:inline-block;width:12px;height:7px;flex-shrink:0;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='7' fill='none'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%233b4262' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:center;
  transition:transform .2s cubic-bezier(.4,0,.2,1);
}
details.panel[open]>summary::after{transform:rotate(180deg)}
details.panel[open]>summary{margin-bottom:16px}

/* ── Forms ── */
form.row,.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
form.col,.col{display:flex;flex-direction:column;gap:10px;align-items:flex-start}
input,select,textarea{
  background:var(--panel2);color:var(--text);
  border:1px solid var(--line2);border-radius:8px;
  padding:8px 12px;font-size:14px;
  outline:none;font-family:inherit;
  transition:border-color .15s,box-shadow .15s;
}
input::placeholder,textarea::placeholder{color:var(--faint)}
input:focus,select:focus,textarea:focus{
  border-color:var(--accent);
  box-shadow:0 0 0 3px var(--accent-soft);
}
select{
  appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23677090' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center;
  padding-right:28px;cursor:pointer;
}
input.url{flex:1;min-width:340px}
textarea{width:100%;resize:vertical;line-height:1.56}
label.chk{
  color:var(--muted);display:flex;gap:6px;align-items:center;
  font-size:13px;user-select:none;cursor:pointer;
}
label.chk:hover{color:var(--text)}
button{
  background:var(--accent);color:#0a0a0b;
  border:none;border-radius:8px;
  padding:8px 16px;font-size:14px;font-weight:640;
  cursor:pointer;letter-spacing:-.01em;
  transition:background .12s,box-shadow .12s,transform .06s;
}
button:hover{
  background:var(--accent-2);
  box-shadow:0 0 18px rgba(20,217,196,.22);
}
button:active{transform:translateY(1px);box-shadow:none}
.hint{color:var(--faint);font-size:12px;line-height:1.5}

/* ── Check result card ── */
.result{
  border:1px solid var(--line2);border-radius:12px;
  padding:16px 20px;background:var(--panel2);margin-top:14px;
  box-shadow:0 2px 6px rgba(0,0,0,.2);
}
.result .t{font-size:16px;font-weight:650;margin:0 0 8px;letter-spacing:-.022em}
.kv{color:var(--muted);font-size:13px;margin:4px 0;line-height:1.5}
.kv b{color:var(--text);font-weight:600}
.verdict{margin-top:12px;font-size:14px}
.fit-c{color:var(--green);font-weight:640}
.nofit{color:var(--red);font-weight:640}

/* ── Table ── */
table{width:100%;border-collapse:collapse}
th{
  text-align:left;color:var(--faint);
  font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;
  font-weight:600;padding:0 10px 12px;white-space:nowrap;
}
td{
  padding:11px 10px;
  border-top:1px solid var(--line);
  vertical-align:middle;
}
tbody tr{transition:background .08s}
tbody tr:hover td{background:rgba(20,217,196,.022)}
td.num{
  color:var(--faint);width:28px;
  font-variant-numeric:tabular-nums;
  font-size:11.5px;text-align:right;padding-right:4px;
}
.score{
  font-variant-numeric:tabular-nums;font-weight:700;
  width:40px;letter-spacing:-.025em;font-size:14px;
  color:var(--text);
}
.fit{
  font-variant-numeric:tabular-nums;font-weight:700;
  color:var(--accent);width:40px;font-size:14px;letter-spacing:-.025em;
}
.tier{font-size:11.5px;color:var(--violet);white-space:nowrap;font-weight:500}
.ctype{font-size:11.5px;color:var(--muted);white-space:nowrap}
.ctype.staffing{color:var(--amber)}
.why{
  color:var(--muted);font-size:12px;
  max-width:280px;display:inline-block;line-height:1.5;
}
.dq{
  color:var(--red);font-size:12px;font-weight:560;
  max-width:280px;display:inline-block;line-height:1.5;
}
.ctxpre{
  background:var(--panel2);border:1px solid var(--line2);border-radius:10px;
  padding:12px 14px;font-size:11.5px;line-height:1.62;white-space:pre-wrap;
  color:var(--muted);max-height:200px;overflow:auto;margin:0;
  font-family:ui-monospace,'Cascadia Code','Fira Code',monospace;letter-spacing:0;
}
.company{font-weight:600;white-space:nowrap;letter-spacing:-.01em}
.cname.loved{color:var(--accent)}
.love{
  margin-left:8px;cursor:pointer;
  color:var(--faint);font-size:12px;opacity:0;
  transition:opacity .12s,color .12s,transform .1s;
  user-select:none;vertical-align:middle;
}
tr:hover .love{opacity:.4}
.love:hover{color:var(--red);opacity:1}
.love:active{transform:scale(1.35)}
.love.on{opacity:1;color:var(--red)}
.role{color:var(--text);max-width:300px;font-weight:500}
.loc{color:var(--muted);font-size:12.5px;max-width:165px}
td a{
  white-space:nowrap;font-size:12px;color:var(--muted);
  padding:4px 9px;border-radius:6px;border:1px solid var(--line2);
  display:inline-flex;align-items:center;
  transition:color .12s,border-color .12s,background .12s;
}
td a:hover{
  color:var(--accent);
  border-color:rgba(20,217,196,.3);
  background:var(--accent-soft);
}

/* ── Status pills ── */
.pill{
  display:inline-block;padding:3px 9px;border-radius:999px;
  font-size:10px;font-weight:600;border:1px solid transparent;
  letter-spacing:.04em;text-transform:uppercase;
}
.pill.auto{color:var(--green);background:rgba(52,211,153,.07);border-color:rgba(52,211,153,.22)}
.pill.confirm{color:var(--amber);background:rgba(251,191,36,.07);border-color:rgba(251,191,36,.22)}
.pill.manual{color:var(--faint);background:rgba(59,66,98,.12);border-color:var(--line2)}

/* ── Empty state ── */
.empty{color:var(--muted);padding:48px 0;text-align:center;font-size:14px}
.emptyrow{color:var(--muted);padding:44px 12px;text-align:center;font-size:14px}
.emptyrow:hover{background:none}

/* ── Pagination ── */
.pager{
  display:flex;align-items:center;justify-content:center;gap:24px;
  margin-top:18px;padding-top:16px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--muted);
}
.pager .faint{color:var(--faint)}
.pager .pageno{font-variant-numeric:tabular-nums;color:var(--text);font-weight:500}

/* ── Modals & overlays ── */
.overlay{
  position:fixed;inset:0;
  background:rgba(3,5,11,.8);
  backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px);
  display:none;align-items:flex-start;justify-content:center;
  z-index:30;padding-top:8vh;
}
#favtoggle:checked ~ .fav-ov{display:flex}
#preftoggle:checked ~ .pref-ov{display:flex}
#ctxtoggle:checked ~ .ctx-ov{display:flex}
.chips{display:flex;flex-wrap:wrap;gap:7px}
.chip{
  background:var(--panel2);border:1px solid var(--line2);
  border-radius:999px;padding:5px 8px 5px 13px;
  font-size:12.5px;font-weight:500;
  display:flex;align-items:center;gap:8px;color:var(--text);
}
.chip .love{opacity:1;margin:0;color:var(--red);font-size:13px}
.modal{
  background:var(--panel);border:1px solid var(--line2);
  border-radius:16px;padding:24px 26px;
  width:min(600px,92vw);position:relative;
  max-height:84vh;overflow:auto;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.028),
    0 32px 96px rgba(0,0,0,.7),
    0 8px 28px rgba(0,0,0,.45);
}
.filein{
  background:var(--panel2);border:1.5px dashed var(--line2);
  border-radius:8px;padding:10px 13px;font-size:13px;
  color:var(--muted);width:100%;cursor:pointer;
  transition:border-color .15s;
}
.filein:hover{border-color:rgba(20,217,196,.3)}
.modal-close{
  position:absolute;top:14px;right:16px;cursor:pointer;
  color:var(--faint);font-size:20px;line-height:1;text-decoration:none;
  width:28px;height:28px;display:flex;align-items:center;justify-content:center;
  border-radius:6px;transition:color .12s,background .12s;
}
.modal-close:hover{color:var(--text);background:var(--panel2)}
.modal-h{
  font-size:10px;text-transform:uppercase;letter-spacing:.14em;
  color:var(--faint);margin:0 0 14px;font-weight:600;
}

.filterbar{padding-bottom:15px;margin-bottom:2px;border-bottom:1px solid var(--line);gap:9px}

.callnav{display:flex;align-items:center;justify-content:center;gap:22px;margin-bottom:16px;
  font-size:13px;color:var(--muted)}
.callnav .callno{font-weight:600;color:var(--text);font-variant-numeric:tabular-nums}
.callnav .faint{color:var(--faint)}

/* ── Review cards (latest-call audit view) ── */
.review{display:flex;flex-direction:column;gap:13px}
.rev-card{background:var(--panel2);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;box-shadow:0 2px 6px rgba(0,0,0,.2)}
.rev-head{display:flex;align-items:flex-start;gap:14px}
.rev-fit{font-variant-numeric:tabular-nums;font-weight:700;font-size:17px;
  color:var(--accent);min-width:32px;letter-spacing:-.02em}
.rev-headmain{flex:1;min-width:0}
.rev-role{font-weight:600;font-size:15px;letter-spacing:-.012em;color:var(--text);
  display:inline-block;transition:color .12s}
.rev-role:hover{color:var(--accent)}
.rev-sub{color:var(--muted);font-size:12.5px;margin-top:3px}
.rev-badge{font-size:10.5px;font-weight:600;padding:3px 10px;border-radius:999px;
  white-space:nowrap;text-transform:uppercase;letter-spacing:.04em}
.rev-badge.pass{color:var(--green);background:rgba(52,211,153,.1);border:1px solid rgba(52,211,153,.3)}
.rev-badge.fail{color:var(--red);background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.3)}
.rev-reason{margin-top:11px;font-size:13px;line-height:1.5}
.rev-reason.pass{color:var(--muted)}
.rev-reason.fail{color:var(--red)}
.rev-dq{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px}
.dqchip{font-size:12px;font-weight:560;color:var(--red);background:rgba(248,113,113,.09);
  border:1px solid rgba(248,113,113,.28);border-radius:6px;padding:4px 10px}
.dqchip[onclick]{cursor:pointer}
.dqchip[onclick]:hover{background:rgba(248,113,113,.16)}
.rev-desc{margin-top:13px;padding:14px 16px;background:var(--panel);border:1px solid var(--line);
  border-radius:9px;font-size:13.5px;line-height:1.7;color:var(--text);
  max-height:260px;overflow:auto}
mark.hl-gate,.hl-gate{color:#ff8f8f;background:rgba(248,113,113,.16);border-radius:3px;
  padding:1px 3px;font-weight:600}
mark.hl-gate.flash{outline:2px solid var(--red);animation:qflash 1.4s ease}
@keyframes qflash{0%,40%{background:rgba(248,113,113,.5)}100%{background:rgba(248,113,113,.16)}}

/* ── Apply-ready card actions ── */
.rev-actions{display:flex;gap:9px;margin-top:14px;flex-wrap:wrap}
.rbtn{font-size:12.5px;font-weight:560;padding:7px 14px;border-radius:7px;cursor:pointer;
  border:1px solid var(--line2);background:var(--panel2);color:var(--text);
  transition:background .12s,border-color .12s,opacity .12s}
.rbtn:hover{background:var(--elevated)}
.rbtn:disabled{opacity:.5;cursor:default}
.rbtn.fill{border-color:rgba(20,217,196,.5);color:var(--accent);background:var(--accent-soft)}
.rbtn.fill:hover{background:rgba(20,217,196,.16)}
.rbtn.done{border-color:rgba(79,175,120,.5);color:var(--green)}
.rbtn.done:hover{background:rgba(79,175,120,.12)}
.rbtn.del{color:var(--faint);margin-left:auto}
.rbtn.del:hover{border-color:rgba(217,111,111,.5);color:var(--red);background:rgba(217,111,111,.08)}
.rev-badge.applied{color:var(--green);background:rgba(79,175,120,.14);border-color:rgba(79,175,120,.4)}
.rev-card.applied{opacity:.5}
.rev-card.applied .rev-actions{display:none}
.rev-card{transition:opacity .3s,transform .3s,max-height .3s}
.rev-card.slideout{opacity:0;transform:translateX(40px);max-height:0;
  margin:0;padding-top:0;padding-bottom:0;overflow:hidden;border-width:0}
.hl-req{color:var(--amber);background:rgba(251,191,36,.08);border-radius:3px;padding:1px 3px}

/* ── View dropdown menu (macOS-style) ── */
.menu{position:relative;display:inline-block;margin-bottom:15px}
.menu>summary{list-style:none;cursor:pointer;user-select:none;display:inline-flex;
  align-items:center;gap:9px;background:var(--panel);border:1px solid var(--line2);
  border-radius:8px;padding:8px 14px;font-size:13px;font-weight:560;color:var(--text)}
.menu>summary::-webkit-details-marker{display:none}
.menu>summary::after{content:'';width:8px;height:5px;flex-shrink:0;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='5' fill='none'%3E%3Cpath d='M1 1l3 3 3-3' stroke='%237b8494' stroke-width='1.3' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:center}
.menu>summary:hover{border-color:var(--accent)}
.menu[open]>summary{border-color:var(--accent)}
.menu-list{position:absolute;top:calc(100% + 6px);left:0;z-index:25;min-width:200px;
  background:var(--panel2);border:1px solid var(--line2);border-radius:11px;padding:6px;
  box-shadow:0 18px 48px rgba(0,0,0,.55);display:flex;flex-direction:column;gap:2px;
  max-height:320px;overflow-y:auto}
.menu-list a{padding:7px 11px;border-radius:7px;font-size:12px;color:var(--text);white-space:nowrap;
  display:flex;align-items:center;justify-content:space-between;gap:16px}
.menu-list a:hover{background:var(--accent);color:#0a0a0b}
.menu-list a.sel{color:var(--accent)}
.menu-list a.sel:hover{color:#0a0a0b}
.mcount{font-size:11px;font-weight:600;color:var(--faint);
  background:var(--panel);border:1px solid var(--line);border-radius:20px;
  padding:1px 7px;min-width:22px;text-align:center;font-variant-numeric:tabular-nums}
.menu-list a:hover .mcount{color:#0a0a0b;background:rgba(0,0,0,.14);border-color:transparent}
.hmenu{margin:0}
.hmenu>summary{background:none;border:none;padding:0 0 12px;gap:5px;color:var(--muted);
  font-size:11px;text-transform:uppercase;letter-spacing:.07em;font-weight:650}
.hmenu>summary:hover{color:var(--text)}
.hmenu[open]>summary{color:var(--accent)}
.hmenu.active>summary{color:var(--accent)}
.filterbar2{display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin:0 0 18px;
  padding:13px 18px;background:var(--panel);border:1px solid var(--line);border-radius:12px}
.filterbar2 .hmenu>summary{padding:0}
.tip{position:relative;display:inline-flex;align-items:center;vertical-align:middle}
.tipmark{margin-left:5px;width:14px;height:14px;border-radius:50%;border:1px solid var(--line2);
  color:var(--faint);font-size:9.5px;font-weight:700;font-style:normal;cursor:help;
  display:inline-flex;align-items:center;justify-content:center;line-height:1}
.tipmark:hover{border-color:var(--accent);color:var(--accent)}
.tipbox{position:absolute;bottom:calc(100% + 9px);left:-6px;width:290px;z-index:60;
  background:var(--panel2);border:1px solid var(--line2);border-radius:10px;padding:12px 14px;
  font-size:12px;line-height:1.55;color:var(--muted);font-weight:400;text-transform:none;
  letter-spacing:normal;white-space:normal;word-break:normal;overflow-wrap:break-word;
  box-shadow:0 16px 44px rgba(0,0,0,.6);text-align:left;
  opacity:0;visibility:hidden;transition:opacity .13s;pointer-events:none}
.tipbox b{color:var(--text);font-weight:640}
.tipbox .k{color:var(--accent);font-weight:640}
.tip:hover .tipbox{opacity:1;visibility:visible}
.srch-list{padding:8px}
.srch{display:flex;gap:6px}
.srch input{min-width:150px;font-size:12.5px}
.srch button{padding:8px 12px;font-size:12.5px}

/* ── Pipeline / flow page ── */
.flowtop{display:flex;align-items:center;justify-content:space-between;margin-bottom:28px;
  padding-bottom:20px;border-bottom:1px solid var(--line)}
.flowtop h1{font-size:19px;font-weight:700;letter-spacing:-.02em;margin:0}
.flowcanvas{background-image:radial-gradient(var(--line2) .8px, transparent .8px);
  background-size:24px 24px;border:1px solid var(--line);border-radius:18px;
  padding:52px 40px;display:flex;align-items:center;min-height:380px}
.flow{display:flex;align-items:stretch;gap:0;flex-wrap:wrap;row-gap:22px;width:100%}
.fnode{flex:1;min-width:205px;background:var(--panel);border:1px solid var(--line);
  border-radius:14px;padding:24px 22px;display:flex;flex-direction:column;gap:14px;
  min-height:250px;box-shadow:0 4px 16px rgba(0,0,0,.25)}
.fcol{flex:1;min-width:205px;display:flex;flex-direction:column;gap:20px}
.fcol .fnode{flex:1;min-height:auto;min-width:0}
.fmerge{width:60px;flex-shrink:0;align-self:stretch}
.fmerge path{fill:none;stroke:var(--line2);stroke-width:2;stroke-dasharray:5 6;
  animation:dashmove 1s linear infinite}
@keyframes dashmove{to{stroke-dashoffset:-22}}
.colist{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.corow{display:flex;align-items:center;gap:12px;padding:15px 17px;border:1px solid var(--line);
  border-radius:11px;background:var(--panel2)}
.corow:hover{border-color:var(--line2)}
.coname{font-weight:600;color:var(--text)}
.coname:hover{color:var(--accent)}
@media(max-width:720px){.colist{grid-template-columns:1fr}}
.covendor{font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;font-weight:600}
.corm{margin-left:auto;background:none;border:1px solid var(--line2);color:var(--muted);
  width:27px;height:27px;border-radius:7px;font-size:16px;padding:0;line-height:1;cursor:pointer}
.corm:hover{color:var(--red);border-color:var(--red)}
.fnode.ready{border-color:var(--accent);box-shadow:0 0 30px var(--accent-soft)}
.fhead{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);
  font-weight:600;display:flex;align-items:center;gap:8px}
.fnum{width:19px;height:19px;border-radius:50%;background:var(--accent);color:#0a0a0b;
  display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0}
.fbig{font-size:42px;font-weight:700;letter-spacing:-.03em;font-variant-numeric:tabular-nums;line-height:1;margin-top:4px}
.fdesc{font-size:12px;color:var(--muted);line-height:1.45}
.fbtn,.fnode button{font-size:12.5px;text-align:center;border-radius:8px;padding:8px 12px;cursor:pointer}
.fbtn{color:var(--accent);border:1px solid var(--line2);background:transparent;transition:border-color .14s}
.fbtn:hover{border-color:var(--accent)}
.fnode textarea{font-size:12px;line-height:1.5}
.freplabel{font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);
  margin:4px 0 2px}
.frep{display:flex;flex-direction:column;gap:2px}
.freprow{display:flex;flex-direction:column;gap:3px;padding:7px 8px;border-radius:8px;
  border:1px solid transparent;cursor:pointer}
.freprow:hover{background:var(--panel2);border-color:var(--accent)}
.freptop{display:flex;align-items:baseline;gap:9px;font-size:12px}
.frepno{color:var(--accent);font-weight:640;font-variant-numeric:tabular-nums;min-width:22px}
.frepn{color:var(--text);font-weight:600;white-space:nowrap;flex:1}
.frepauto{color:var(--green);font-weight:600;white-space:nowrap}
.frepmeta{color:var(--info);font-weight:600;white-space:nowrap}
.frepsub{font-size:11px;color:var(--muted);padding-left:31px;letter-spacing:.01em;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fpending{font-size:12px;font-weight:560;color:var(--faint);margin:2px 0 12px}
.fpending.on{color:var(--accent)}
.freparrow{color:var(--accent);opacity:0;transition:opacity .12s;font-weight:600}
.freprow:hover .freparrow{opacity:1}
.kwlist{display:flex;flex-direction:column;gap:6px;width:100%;
  max-height:270px;overflow-y:auto;padding-right:3px}
.kwrow{display:flex;align-items:center;gap:8px;background:var(--panel2);
  border:1px solid var(--line);border-radius:8px;padding:8px 8px 8px 11px}
.kwname{font-size:12.5px;color:var(--text);flex:1;min-width:0;line-height:1.35;word-break:break-word}
.kwrm{margin-left:auto;flex-shrink:0;background:none;border:none;color:var(--faint);
  font-size:16px;line-height:1;padding:0;width:20px;height:20px;cursor:pointer}
.kwrm:hover{color:var(--red)}
.kwadd{display:flex;gap:6px;margin-top:11px;width:100%}
.kwadd input{flex:1;min-width:0}
.kwadd button{padding:8px 13px;flex-shrink:0}
.fconn{align-self:center;position:relative;width:62px;height:2px;flex-shrink:0;
  background:repeating-linear-gradient(90deg,var(--line2) 0 5px,transparent 5px 11px)}
.fconn::after{content:'';position:absolute;top:-3px;left:0;width:8px;height:8px;border-radius:50%;
  background:var(--accent);box-shadow:0 0 10px var(--accent);animation:packet 1.9s linear infinite}
@keyframes packet{0%{left:0;opacity:0}12%{opacity:1}88%{opacity:1}100%{left:calc(100% - 8px);opacity:0}}
@media(max-width:820px){.fconn{display:none}.fnode{min-width:44%}}
.hmenu .menu-list{top:calc(100% - 4px)}
th.hdd{padding-bottom:0}
a.cname{color:var(--text);transition:color .12s}
a.cname:hover{color:var(--accent)}
a.cname.loved{color:var(--accent)}
.actions{white-space:nowrap;display:flex;align-items:center;gap:12px;justify-content:flex-end}
.pin{cursor:pointer;color:var(--faint);font-size:14px;opacity:0;
  transition:opacity .12s,color .12s,transform .1s;user-select:none}
tr:hover .pin{opacity:.55}
.pin:hover{color:var(--amber)}
.pin:active{transform:scale(1.25)}
.pin.on{opacity:1;color:var(--amber)}
"""

_TIER_LABEL = {"voice_speech": "voice", "ai_ml": "ai/ml", "swe_backend": "swe"}
_TYPE_LABEL = {"yc_early": "YC/early", "funded_startup": "startup", "unicorn": "unicorn",
               "public_corp": "public", "staffing_proxy": "staffing", "unknown": "—"}
_PAGE = 20
_AUTO_SQL = ("(source LIKE 'greenhouse%' OR source LIKE 'lever%' OR source LIKE 'ashby%' "
             "OR source LIKE 'workday%' OR url LIKE '%greenhouse.io%' OR url LIKE '%lever.co%' "
             "OR url LIKE '%ashbyhq.com%' OR url LIKE '%myworkdayjobs.com%')")
_CONF_SQL = "(url LIKE '%indeed.com%' OR url LIKE '%linkedin.com%' OR url LIKE '%glassdoor%')"
# Jobs a "Run call" will deep-read next: shortlisted (score>=60) but not yet analyzed.
_PENDING_SQL = "score >= 60 AND afit IS NULL AND status != 'closed'"

_SCORE_TIP = ("<b>Score</b> — a fast keyword match on the job <b>title</b> only. Built from your "
              "tier ladder (<span class=k>voice/speech &gt; AI/ML &gt; SWE</span>) plus title "
              "keyword hits and a big boost for <span class=k>junior / entry / new-grad</span> "
              "titles. It never reads the description, so it just surfaces relevant-looking roles "
              "fast. Use it to scan breadth — not as proof you'll get in. Trust <b>Fit</b> for that.")
_FIT_TIP = ("<b>Fit</b> — Claude reads the <b>full description against your resume &amp; profile</b> "
            "and estimates your realistic odds of landing an interview/offer if you apply "
            "(<span class=k>0–100</span>), weighing required years, degree, sponsorship, and how "
            "competitive the role is. This is the number to prioritize by: high Fit = actually worth "
            "applying; low Fit = a stretch even if the Score looks good.")
_MATCH_TIP = ("<b>Match</b> — how well a job matches the <b>preference sentence</b> you typed in the "
              "'rank by preference' box (<span class=k>0–100</span>) — about your stated interests, "
              "not your odds of getting in. For odds, use <b>Fit</b> on the analyzed cards.")


def _tip(text: str) -> str:
    return f"<span class=tip><span class=tipmark>i</span><span class=tipbox>{text}</span></span>"


def _apply_filters(q: str, p: list, tier, ctype, company, locf, af) -> tuple[str, list]:
    """Append the shared column filters (tier/type/company/location/apply) to any
    view's query, so filtering works the same everywhere."""
    if tier:
        q += " AND tier = ?"; p.append(tier)
    if ctype:
        q += " AND company_type = ?"; p.append(ctype)
    if company:
        q += " AND company LIKE ?"; p.append(f"%{company}%")
    if locf == "remote":
        q += " AND remote = 1"
    elif locf == "hybrid":
        q += " AND (lower(location) LIKE '%hybrid%' OR lower(description) LIKE '%hybrid%')"
    elif locf:                                       # a US state code
        q += " AND location LIKE ?"; p.append(f"%, {locf}%")
    if af == "auto":
        q += f" AND {_AUTO_SQL}"
    elif af == "confirm":
        q += f" AND {_CONF_SQL} AND NOT {_AUTO_SQL}"
    elif af == "manual":
        q += f" AND NOT {_AUTO_SQL} AND NOT {_CONF_SQL}"
    return q, p


def _dim_counts(conn, where: str, params: list) -> dict:
    """Breakdown counts over the current population, per dropdown dimension, so
    each menu can show how many jobs fall in each category without switching."""
    def grp(col):
        d = {}
        for r in conn.execute(f"SELECT {col} k, COUNT(*) n FROM jobs "
                              f"WHERE {where} GROUP BY {col}", params):
            d[r["k"] or ""] = r["n"]
        return d

    def one(extra):
        return conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {where}{extra}",
                            params).fetchone()[0]
    total = one("")
    tier = grp("tier"); tier[""] = total
    ctype = grp("company_type"); ctype[""] = total
    auto = one(f" AND {_AUTO_SQL}")
    conf = one(f" AND {_CONF_SQL} AND NOT {_AUTO_SQL}")
    af = {"": total, "auto": auto, "confirm": conf, "manual": total - auto - conf}
    locf = {"": total, "remote": one(" AND remote = 1"),
            "hybrid": one(" AND (lower(location) LIKE '%hybrid%' "
                          "OR lower(description) LIKE '%hybrid%')")}
    import re
    for r in conn.execute(f"SELECT location FROM jobs WHERE {where}", params):
        for st in re.findall(r",\s*([A-Z]{2})\b", r[0] or ""):   # per-state counts
            locf[st] = locf.get(st, 0) + 1
    return {"tier": tier, "ctype": ctype, "af": af, "locf": locf}
_US_STATES = [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"),
    ("CA", "California"), ("CO", "Colorado"), ("CT", "Connecticut"), ("DE", "Delaware"),
    ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"),
    ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"),
    ("KY", "Kentucky"), ("LA", "Louisiana"), ("ME", "Maine"), ("MD", "Maryland"),
    ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"), ("MS", "Mississippi"),
    ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"), ("NV", "Nevada"),
    ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"), ("NY", "New York"),
    ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"),
    ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"), ("SC", "South Carolina"),
    ("SD", "South Dakota"), ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"),
    ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"), ("WV", "West Virginia"),
    ("WI", "Wisconsin"), ("WY", "Wyoming"), ("DC", "Washington DC"),
]


def _tabs(view: str, base: dict) -> str:
    from urllib.parse import urlencode
    items = [("", "All jobs"), ("apply", "Apply-ready"),
             ("rejected", "Rejected")]
    labels = dict(items)
    links = "".join(
        f"<a href='?{urlencode({**base, 'view': v, 'page': 0, 'fetch': 0, 'sort': ''})}'"
        f"{' class=sel' if v == view else ''}>{lbl}</a>"
        for v, lbl in items)
    return (f"<details class=menu name=hdr><summary>{labels.get(view, 'All jobs')}</summary>"
            f"<div class=menu-list>{links}</div></details>")


def _pager(page: int, has_next: bool, base: dict) -> str:
    from urllib.parse import urlencode
    if page == 0 and not has_next:
        return ""
    prev = (f"<a href='?{urlencode({**base, 'page': page - 1})}'>← prev</a>"
            if page > 0 else "<span class=faint>← prev</span>")
    nxt = (f"<a href='?{urlencode({**base, 'page': page + 1})}'>next →</a>"
           if has_next else "<span class=faint>next →</span>")
    return f"<div class=pager>{prev}<span class=pageno>page {page + 1}</span>{nxt}</div>"


def _toggles() -> str:
    return ("<input type=checkbox id=favtoggle hidden>"
            "<input type=checkbox id=preftoggle hidden>"
            "<input type=checkbox id=ctxtoggle hidden>")


def _toolbar() -> str:
    return (
        "<div class=toolbar>"
        "<a class=tool-btn href='/flow'>&#9781;&nbsp; Pipeline</a>"
        "<label for=ctxtoggle class=tool-btn>&#9998;&nbsp; Resume</label>"
        "<label for=preftoggle class=tool-btn>&#10022;&nbsp; Preference</label>"
        "<label for=favtoggle class=heart-btn title='Loved companies'>&#9829;</label>"
        "</div>"
    )


def _context_modal() -> str:
    from .core.config import analyze_prompt, resume_text
    from .match.analyze import _profile_block
    resume, prompt = resume_text(), analyze_prompt()
    return (
        "<div class='overlay ctx-ov'><div class=modal>"
        "<label for=ctxtoggle class=modal-close>&times;</label>"
        "<div class=modal-h>Your resume</div>"
        "<form class=col method=post action='/resume' enctype='multipart/form-data'>"
        "<input class=filein type=file name=file accept='.txt,.md,.pdf'>"
        f"<textarea name=resume rows=9 style='width:100%' "
        f"placeholder='…or paste it as plain text'>{_e(resume)}</textarea>"
        "<div class=row><button type=submit>Save resume</button>"
        "<span class=hint>upload a .pdf/.txt or paste · then <code>analyze --force</code></span></div>"
        "</form>"
        "<div class=modal-h style='margin-top:22px'>What Claude sees — profile</div>"
        f"<pre class=ctxpre>{_e(_profile_block())}</pre>"
        "<div class=modal-h style='margin-top:22px'>Claude prompt · advanced</div>"
        "<form class=col method=post action='/prompt'>"
        f"<textarea name=prompt rows=10 style='width:100%;font-family:ui-monospace,monospace;"
        f"font-size:12px'>{_e(prompt)}</textarea>"
        "<div class=row><button type=submit>Save prompt</button>"
        "<span class=hint>keep &lt;&lt;PROFILE&gt;&gt; &lt;&lt;RESUME&gt;&gt; &lt;&lt;JOBS&gt;&gt; markers</span></div>"
        "</form></div></div>"
    )


def _fav_modal() -> str:
    from .core.favorites import loved_companies
    loved = sorted(loved_companies())
    chips = "".join(
        f"<span class=chip data-c=\"{_e(c)}\">{_e(c)}<span class='love on chip-x' "
        f"data-c=\"{_e(c)}\" onclick='love(this)'>&#9829;</span></span>" for c in loved)
    hint = ("" if loved else
            "<div class=hint>No loved companies yet — tap the ♥ next to any company.</div>")
    loved_html = f"<div class=chips id=favchips>{chips}</div>{hint}"
    return (
        "<div class='overlay fav-ov'><div class=modal>"
        "<label for=favtoggle class=modal-close>&times;</label>"
        "<div class=modal-h>Loved companies</div>"
        f"{loved_html}"
        "<div class=modal-h style='margin-top:22px'>Add a company by link</div>"
        "<form class=col method=post action='/add'>"
        "<input class=url type=text name=url style='width:100%' "
        "placeholder='Paste a careers link — Greenhouse / Lever / Ashby / Workday…'>"
        "<div class=row><button type=submit>Add &amp; fetch</button>"
        "<span class=hint>scanned on every future search via their ATS</span></div>"
        "</form></div></div>"
    )


def _pref_modal() -> str:
    from .core.favorites import load_preference
    pref = load_preference()
    ph = ("Describe what you want in plain English — e.g. “early-career engineer, "
          "need visa sponsorship, love voice / speech AI but open to backend, no senior "
          "roles, no internships, NYC or remote”")
    return (
        "<div class='overlay pref-ov'><div class=modal>"
        "<label for=preftoggle class=modal-close>&times;</label>"
        "<div class=modal-h>Rank by preference &nbsp;·&nbsp; AI</div>"
        "<form class=col method=post action='/rank'>"
        f"<textarea name=preference rows=3 style='width:100%' placeholder=\"{_e(ph)}\">{_e(pref)}</textarea>"
        "<input type=hidden name=tier value=''>"
        "<input type=hidden name=min_score value=40>"
        "<div class=row><button type=submit>Rank with Claude</button>"
        "<span class=hint>uses your Claude Pro CLI · free · may take ~30s</span></div>"
        "</form></div></div>"
    )


def _page(body: str) -> str:
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>jobhunt</title><style>{CSS}</style></head>"
            f"<body>{_toggles()}{_fav_modal()}{_pref_modal()}{_context_modal()}"
            f"<div class=wrap>{body}</div>{_JS}</body></html>")


_JS = """<script>
function love(el){
  var c=el.dataset.c;
  var f=new FormData(); f.append('company', c);
  fetch('/love',{method:'POST',body:f}).then(function(r){return r.json();})
    .then(function(d){
      document.querySelectorAll('.love').forEach(function(x){
        if(x.dataset.c===c){
          x.classList.toggle('on', d.loved);
          var n=x.parentNode.querySelector('.cname'); if(n) n.classList.toggle('loved', d.loved);
        }
      });
      var box=document.getElementById('favchips');
      if(box){
        var found=null;
        box.querySelectorAll('.chip').forEach(function(ch){ if(ch.getAttribute('data-c')===c) found=ch; });
        if(d.loved && !found){
          var s=document.createElement('span'); s.className='chip'; s.setAttribute('data-c',c);
          s.appendChild(document.createTextNode(c));
          var h=document.createElement('span'); h.className='love on chip-x'; h.dataset.c=c;
          h.setAttribute('onclick','love(this)'); h.innerHTML=' &#9829;';
          s.appendChild(h); box.appendChild(s);
        } else if(!d.loved && found){ found.remove(); }
      }
    });
}
function pin(el){
  var f=new FormData(); f.append('id', el.dataset.i);
  fetch('/pin',{method:'POST',body:f}).then(function(r){return r.json();})
    .then(function(d){ el.classList.toggle('on', d.pinned); });
}
function jumpq(el){
  var t=document.getElementById(el.dataset.t);
  if(t){ t.scrollIntoView({block:'center',behavior:'smooth'});
    t.classList.add('flash'); setTimeout(function(){t.classList.remove('flash');},1400); }
}
document.addEventListener('click',function(e){
  document.querySelectorAll('details.menu[open]').forEach(function(d){
    if(!d.contains(e.target)) d.removeAttribute('open');   // close dropdowns on outside click
  });
});
function applyfill(el){
  var old=el.textContent; el.disabled=true; el.textContent='Opening browser…';
  fetch('/apply/'+el.dataset.i,{method:'POST'}).then(function(r){return r.json();})
    .then(function(d){ el.textContent = d.ok ? 'Opened ↗ — fill & submit' : (d.error||'No apply URL');
      setTimeout(function(){el.disabled=false; el.textContent=old;}, 5000); })
    .catch(function(){ el.disabled=false; el.textContent=old; });
}
function markApplied(el){
  var f=new FormData(); f.append('id', el.dataset.i);
  fetch('/applied',{method:'POST',body:f}).then(function(){
    var card=el.closest('.rev-card');
    var b=card.querySelector('.rev-badge');
    if(b){ b.textContent='applied'; b.className='rev-badge applied'; }
    card.classList.add('applied');
  });
}
function dismissJob(el){
  var f=new FormData(); f.append('id', el.dataset.i);
  var card=el.closest('.rev-card');
  card.style.maxHeight=card.offsetHeight+'px';
  fetch('/dismiss',{method:'POST',body:f}).then(function(){
    requestAnimationFrame(function(){ card.classList.add('slideout'); });
    setTimeout(function(){ card.remove(); }, 340);
  });
}
</script>"""


def _e(v) -> str:
    return html.escape(str(v or ""))


def _header(total: int | None = None, fresh: int | None = None) -> str:
    meta = ""
    if total is not None:
        bits = [f"<b>{total}</b> tracked"]
        if fresh:
            bits.append(f"<b>{fresh}</b> new · 24h")
        meta = f"<div class=meta>{' &nbsp;·&nbsp; '.join(bits)}</div>"
    return (f"<header><div class=brandwrap>"
            f"<a href='/' class=brand>jobhunt<span class=dot></span></a>{meta}</div>"
            f"{_toolbar()}</header>")


def _check_form(url: str = "") -> str:
    return (
        "<div class=panel><h2>Check a job link</h2>"
        "<form class=row method=post action='/check'>"
        f"<input class=url type=text name=url placeholder='Paste a job posting URL…' value='{_e(url)}'>"
        "<label class=chk><input type=checkbox name=save value=1> save if it fits</label>"
        "<button type=submit>Check</button>"
        "</form></div>"
    )


def _filters(tier: str, min_score: int, fresh: bool, sort: str, view: str,
             min_fit: int) -> str:
    topts = [("", "all tiers"), ("voice_speech", "voice"),
             ("ai_ml", "ai/ml"), ("swe_backend", "swe")]
    tsel = "".join(
        f"<option value='{v}'{' selected' if v == tier else ''}>{lbl}</option>"
        for v, lbl in topts)
    fchk = " checked" if fresh else ""
    return (
        "<form class='row filterbar' method=get action='/'>"
        f"<select name=tier>{tsel}</select>"
        f"<input type=number name=min_score value={min_score} style='width:82px' title='min score'>"
        f"<label class=chk><input type=checkbox name=fresh value=1{fchk}> 24h</label>"
        f"<label class=chk>min fit <input type=number name=min_fit value={min_fit} "
        f"style='width:56px' title='AI fit cutoff'></label>"
        f"<input type=hidden name=view value='{_e(view)}'>"
        f"<input type=hidden name=sort value='{_e(sort)}'>"
        "<button type=submit>Apply</button>"
        "</form>"
    )


def _why_cell(analysis: str | None, rejected: bool) -> str:
    """Color-coded 'why' — red disqualifiers for rejects, muted reason otherwise."""
    if not analysis:
        return ""
    try:
        a = json.loads(analysis) or {}
    except Exception:
        return ""
    dq = a.get("disqualifiers") or []
    if rejected and dq:
        return f"<span class=dq>{_e(' · '.join(dq))}</span>"
    return f"<span class=why>{_e(a.get('reason', ''))}</span>"


def _states_present(conn) -> list:
    """Only the US states that actually have jobs — no dead-end options."""
    import re
    present = set()
    for r in conn.execute("SELECT DISTINCT location FROM jobs WHERE status != 'closed'"):
        for m in re.findall(r",\s*([A-Z]{2})\b", r[0] or ""):
            present.add(m)
    return [(c, n) for c, n in _US_STATES if c in present]


def _hmenu(label: str, param: str, cur, opts, base: dict, counts: dict | None = None,
           plain_for: tuple = ()) -> str:
    from urllib.parse import urlencode
    sel = next((lbl for v, lbl in opts if v != "" and str(v) == str(cur)), "")
    if str(cur) in (str(x) for x in plain_for):      # keep the header compact
        sel = ""
    summ = f"{label}: {sel}" if sel else label
    active = " active" if sel else ""

    def cnt(v):
        if counts is None or v not in counts:
            return ""
        return f"<span class=mcount>{counts[v]}</span>"
    links = "".join(
        f"<a href='?{urlencode({**base, param: v, 'page': 0})}'"
        f"{' class=sel' if str(v) == str(cur) else ''}>{lbl}{cnt(v)}</a>" for v, lbl in opts)
    return (f"<details class='menu hmenu{active}' name=hdr><summary>{summ}</summary>"
            f"<div class=menu-list>{links}</div></details>")


def _search_menu(label: str, param: str, cur: str, base: dict) -> str:
    active = " active" if cur else ""
    summ = f"{label}: {_e(cur)}" if cur else label
    hidden = "".join(f"<input type=hidden name={k} value='{_e(v)}'>"
                     for k, v in base.items() if k != param and str(v) not in ("", "0"))
    form = (f"<form class=srch method=get action='/'>{hidden}"
            f"<input type=text name={param} value=\"{_e(cur)}\" placeholder='Type a company…'>"
            f"<button type=submit>Go</button></form>")
    return (f"<details class='menu hmenu{active}' name=hdr><summary>{summ}</summary>"
            f"<div class='menu-list srch-list'>{form}</div></details>")


def _table(rows, fitcol, loved: set, show_why: bool = False, base: dict | None = None,
           tier: str = "", sort: str = "", ctype: str = "", locf: str = "", af: str = "",
           loc_states=None, company: str = "", counts: dict | None = None) -> str:
    base = base or {}
    c = counts or {}
    fit_h = f"<th>Match {_tip(_MATCH_TIP)}</th>" if fitcol else ""
    why_h = "<th>Why</th>" if show_why else ""
    score_h = _hmenu("Score", "sort", sort,
                     [("", "High → Low"), ("score_asc", "Low → High"),
                      ("fetch", "Latest fetch")], base, plain_for=("fetch",))
    tier_h = _hmenu("Tier", "tier", tier, [("", "All"), ("voice_speech", "Voice"),
                    ("ai_ml", "AI/ML"), ("swe_backend", "SWE")], base, c.get("tier"))
    type_h = _hmenu("Type", "ctype", ctype, [("", "All"), ("funded_startup", "Startup"),
                    ("unicorn", "Unicorn"), ("public_corp", "Public"),
                    ("staffing_proxy", "Staffing"), ("yc_early", "YC")], base, c.get("ctype"))
    loc_h = _hmenu("Location", "locf", locf,
                   [("", "All"), ("remote", "Remote"), ("hybrid", "Hybrid")]
                   + (loc_states or []), base, c.get("locf"))
    apply_h = _hmenu("Apply", "af", af, [("", "All"), ("auto", "Auto"),
                     ("confirm", "Confirm"), ("manual", "Manual")], base, c.get("af"))
    head = (f"<table><thead><tr><th></th>{fit_h}<th class=hdd>{score_h}{_tip(_SCORE_TIP)}</th>"
            f"<th class=hdd>{tier_h}</th><th class=hdd>{type_h}</th>"
            f"<th class=hdd>{_search_menu('Company', 'company', company, base)}</th>"
            f"<th>Role</th><th class=hdd>{loc_h}</th>{why_h}"
            f"<th class=hdd>{apply_h}</th><th></th>"
            "</tr></thead><tbody>")
    if not rows:
        return (head + "<tr><td colspan=20 class=emptyrow>No jobs match these "
                "filters — change a column filter above, or run "
                "<code>jobhunt source</code> / <code>analyze</code>."
                "</td></tr></tbody></table>")
    body = []
    for i, r in enumerate(rows, 1):
        path = apply_path(classify_url(r["url"] or "", r["source"] or ""))
        loc = "Remote" if r["remote"] else (r["location"] or "—")
        fit_c = f"<td class=fit>{r[fitcol] if r[fitcol] is not None else '—'}</td>" if fitcol else ""
        ctype = r["company_type"]
        ct_cls = " staffing" if ctype == "staffing_proxy" else ""
        why_c = f"<td>{_why_cell(r['analysis'], rejected=not r['apply_ok'])}</td>" if show_why else ""
        comp = r["company"] or ""
        on = " on" if comp in loved else ""
        cn = " loved" if comp in loved else ""
        curl = r["url"] or "#"
        heart = (f"<a class=\"cname{cn}\" href='{_e(curl)}' target=_blank rel=noopener>{_e(comp)}</a>"
                 f"<span class='love{on}' data-c=\"{_e(comp)}\" onclick='love(this)' "
                 f"title='favorite company'>&#9829;</span>")
        pn = " on" if r["pinned"] else ""
        body.append(
            f"<tr><td class=num>{i}</td>{fit_c}"
            f"<td class=score>{r['score']}</td>"
            f"<td class=tier>{_TIER_LABEL.get(r['tier'], r['tier'] or '—')}</td>"
            f"<td class='ctype{ct_cls}'>{_TYPE_LABEL.get(ctype, '—')}</td>"
            f"<td class=company>{heart}</td>"
            f"<td class=role>{_e(r['title'])}</td>"
            f"<td class=loc>{_e(loc)}</td>{why_c}"
            f"<td><span class='pill {path}'>{path}</span></td>"
            f"<td class=actions>"
            f"<span class='pin{pn}' data-i='{r['id']}' onclick='pin(this)' "
            f"title='add to apply list'>&#9733;</span>"
            f"<a href='{_e(curl)}' target=_blank rel=noopener>open ↗</a></td></tr>"
        )
    return head + "".join(body) + "</tbody></table>"


def _review_cards(rows) -> str:
    if not rows:
        return ("<div class=panel><div class=empty>Nothing analyzed yet — run "
                "<code>jobhunt analyze</code>.</div></div>")
    from .highlight import highlight_html
    cards = []
    for r in rows:
        try:
            a = json.loads(r["analysis"]) or {}
        except Exception:
            a = {}
        rejected = not (r["apply_ok"] or r["pinned"])
        applied = r["status"] == "applied"
        reason_cls = "fail" if rejected else "pass"
        if applied:
            badge = "<span class='rev-badge applied'>applied</span>"
        else:
            badge = (f"<span class='rev-badge {reason_cls}'>"
                     f"{'rejected' if rejected else 'apply-ready'}</span>")
        dq = a.get("disqualifiers") or []
        chips, marks = [], []
        for i, d in enumerate(dq):
            label, quote = (d.get("label", ""), d.get("quote", "")) if isinstance(d, dict) else (str(d), "")
            if quote:
                qid = f"q-{r['id']}-{i}"
                marks.append((qid, quote))
                chips.append(f"<span class=dqchip data-t='{qid}' onclick='jumpq(this)'>"
                             f"{_e(label)} &#9660;</span>")
            else:
                chips.append(f"<span class=dqchip>{_e(label)}</span>")
        dq_html = f"<div class=rev-dq>{''.join(chips)}</div>" if chips else ""
        desc = (_highlight_quotes(r["description"] or "", marks) if marks
                else highlight_html(r["description"] or ""))
        loc = "Remote" if r["remote"] else (r["location"] or "—")
        afit = r["afit"] if r["afit"] is not None else "—"
        actions = ""
        if not rejected:
            actions = (
                f"<div class=rev-actions>"
                f"<button class='rbtn fill' data-i='{r['id']}' onclick='applyfill(this)'>"
                f"Fill application &#8599;</button>"
                f"<button class='rbtn done' data-i='{r['id']}' onclick='markApplied(this)'>"
                f"Mark applied</button>"
                f"<button class='rbtn del' data-i='{r['id']}' onclick='dismissJob(this)'>"
                f"Delete</button></div>")
        card_cls = "rev-card applied" if applied else "rev-card"
        cards.append(
            f"<div class='{card_cls}'><div class=rev-head>"
            f"<span class=rev-fit>{afit}</span>{_tip(_FIT_TIP)}"
            "<div class=rev-headmain>"
            f"<a class=rev-role href='{_e(r['url'] or '#')}' target=_blank rel=noopener>"
            f"{_e(r['title'])} &#8599;</a>"
            f"<div class=rev-sub>{_e(r['company'])} &middot; "
            f"{_TYPE_LABEL.get(r['company_type'], '—')} &middot; {_e(loc)}</div></div>"
            f"{badge}</div>"
            f"<div class='rev-reason {reason_cls}'>{_e(a.get('reason', ''))}</div>"
            f"{dq_html}<div class=rev-desc>{desc}</div>{actions}</div>"
        )
    return "<div class='panel review'>" + "".join(cards) + "</div>"


def _highlight_quotes(desc: str, marks: list) -> str:
    """Wrap the exact JD quotes (Claude's evidence) in clickable red marks."""
    safe = html.escape(desc or "")
    for qid, quote in marks:
        q = html.escape((quote or "").strip())
        if q and q in safe:
            safe = safe.replace(q, f"<mark class=hl-gate id='{qid}'>{q}</mark>", 1)
    return safe.replace("\n", "<br>")


def _render(tier: str, min_score: int, fresh: bool, sort: str,
            preference: str = "", notice: str = "", view: str = "",
            min_fit: int = 50, page: int = 0, ctype: str = "",
            locf: str = "", af: str = "", company: str = "", run: int = 0,
            fetch: int = 0) -> str:
    from .core.favorites import load_preference, loved_companies
    if not preference:
        preference = load_preference()
    loved = loved_companies()

    call_runs, cur_run = [], 0
    fetch_runs, cur_fetch, in_fetch = [], 0, False
    if view in ("apply", "rejected"):
        # Card views, browsable by analysis "call". run=0 (default) = all calls;
        # stepping into a call shows just what that call passed / filtered out.
        with db.connect() as _c:
            call_runs = [r[0] for r in _c.execute(
                "SELECT DISTINCT analysis_run FROM jobs WHERE analysis_run IS NOT NULL "
                "AND status != 'closed' ORDER BY analysis_run DESC").fetchall()]
        cur_run = run if run in call_runs else 0
        if view == "apply":
            base_where, base_p = "(apply_ok = 1 OR pinned = 1) AND status != 'closed'", []
        else:
            base_where, base_p = "analysis IS NOT NULL AND apply_ok = 0 AND status != 'closed'", []
        if cur_run:
            base_where += " AND analysis_run = ?"; base_p.append(cur_run)
        order, fitcol = " ORDER BY afit IS NULL, afit DESC", "afit"
    else:
        # All jobs: always-on fetch bar. A batch is selected explicitly (fetch>0)
        # or via "Latest fetch" (sort=fetch); cur_fetch=0 means "all fetches".
        with db.connect() as _c:
            fetch_runs = [r[0] for r in _c.execute(
                "SELECT DISTINCT fetch_run FROM jobs WHERE fetch_run IS NOT NULL "
                "AND status != 'closed' ORDER BY fetch_run DESC").fetchall()]
        if sort == "fetch" and fetch == 0:
            cur_fetch = fetch_runs[0] if fetch_runs else 0
        elif fetch in fetch_runs:
            cur_fetch = fetch
        in_fetch = cur_fetch > 0
        base_where, base_p = "score >= ? AND status != 'closed'", [min_score]
        if in_fetch:
            base_where += " AND fetch_run = ?"; base_p.append(cur_fetch)
        if fresh:
            base_where += " AND fetched_at >= datetime('now','-24 hours')"
        if sort == "fit":
            order, fitcol = " ORDER BY fit IS NULL, fit DESC, score DESC", "fit"
        elif sort == "score_asc":
            order, fitcol = " ORDER BY score ASC, fetched_at DESC", None
        else:                                    # "", "fetch" → score high→low
            order, fitcol = " ORDER BY score DESC, fetched_at DESC", None

    # Shared column filters apply to EVERY view. Counts are computed over the
    # view's population (before these filters) so the breakdown stays visible.
    q = f"SELECT * FROM jobs WHERE {base_where}"
    p = list(base_p)
    q, p = _apply_filters(q, p, tier, ctype, company, locf, af)
    q += order + f" LIMIT {_PAGE + 1} OFFSET {page * _PAGE}"
    with db.connect() as conn:
        rows = conn.execute(q, p).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        fresh_n = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE fetched_at >= datetime('now','-24 hours')"
        ).fetchone()[0]
        avail_states = _states_present(conn)
        dim_counts = _dim_counts(conn, base_where, list(base_p))
    has_next = len(rows) > _PAGE
    rows = rows[:_PAGE]
    base = {"view": view, "tier": tier, "min_score": min_score,
            "fresh": 1 if fresh else 0, "sort": sort, "min_fit": min_fit,
            "ctype": ctype, "locf": locf, "af": af, "company": company,
            "run": cur_run, "fetch": cur_fetch}
    notice_html = f"<div class=result>{notice}</div>" if notice else ""
    tabs = _tabs(view, base)
    if view in ("apply", "rejected"):
        content = (tabs + _run_nav(cur_run, call_runs, base, view)
                   + _filter_bar(base, tier, ctype, locf, af, company, dim_counts, avail_states)
                   + _review_cards(rows) + _pager(page, has_next, base))
    else:
        content = (tabs + _fetch_nav(cur_fetch, fetch_runs, base) + "<div class=panel>"
                   + _table(rows, fitcol, loved, False, base, tier, sort, ctype, locf, af,
                            avail_states, company, dim_counts)
                   + _pager(page, has_next, base) + "</div>")
    return _page(
        _header(total, fresh_n)
        + notice_html
        + _check_form()
        + content
    )


def _fetch_report(conn, limit: int = 6) -> str:
    """Compact per-fetch-run breakdown for the pipeline page: how many new jobs,
    split by tier and how many land on an auto-fillable ATS."""
    runs = [r[0] for r in conn.execute(
        "SELECT DISTINCT fetch_run FROM jobs WHERE fetch_run IS NOT NULL "
        "AND status != 'closed' ORDER BY fetch_run DESC").fetchall()]
    if not runs:
        return ""
    tier_labels = [("voice_speech", "voice"), ("ai_ml", "ai/ml"), ("swe_backend", "swe")]
    lines = []
    for fr in runs[:limit]:
        w, pr = "fetch_run = ? AND status != 'closed'", [fr]
        total = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {w}", pr).fetchone()[0]
        tiers = {r[0] or "": r[1] for r in conn.execute(
            f"SELECT tier, COUNT(*) FROM jobs WHERE {w} GROUP BY tier", pr)}
        auto = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {w} AND {_AUTO_SQL}", pr).fetchone()[0]
        tb = " &middot; ".join(f"{lbl} {tiers[k]}" for k, lbl in tier_labels if tiers.get(k))
        lines.append(
            f"<a class=freprow href='/?sort=fetch&fetch={fr}'>"
            f"<div class=freptop><span class=frepno>#{fr}</span>"
            f"<span class=frepn>{total} new</span>"
            f"<span class=frepmeta>{auto} auto-apply</span>"
            f"<span class=freparrow>&rarr;</span></div>"
            f"<div class=frepsub>{tb or '—'}</div></a>")
    return f"<div class=frep>{''.join(lines)}</div>"


def _call_report(conn, limit: int = 6) -> str:
    """Per-analysis-call breakdown for the pipeline page: how many JDs Claude read,
    how many passed your gates vs got filtered out. Rows link to that call."""
    runs = [r[0] for r in conn.execute(
        "SELECT DISTINCT analysis_run FROM jobs WHERE analysis_run IS NOT NULL "
        "AND status != 'closed' ORDER BY analysis_run DESC").fetchall()]
    if not runs:
        return ""
    lines = []
    for cr in runs[:limit]:
        w, pr = "analysis_run = ? AND status != 'closed'", [cr]
        total = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {w}", pr).fetchone()[0]
        passed = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {w} AND apply_ok = 1", pr).fetchone()[0]
        lines.append(
            f"<a class=freprow href='/?view=apply&run={cr}'>"
            f"<div class=freptop><span class=frepno>#{cr}</span>"
            f"<span class=frepn>{total} read</span>"
            f"<span class=frepauto>{passed} passed</span>"
            f"<span class=freparrow>&rarr;</span></div>"
            f"<div class=frepsub>{total - passed} filtered out</div></a>")
    return f"<div class=frep>{''.join(lines)}</div>"


def _fetch_nav(cur: int, runs: list, base: dict) -> str:
    """Always-on fetch bar. cur=0 shows 'All fetches · latest #N →'; inside a
    batch it steps earlier/later and offers a way back to all fetches."""
    from urllib.parse import urlencode
    if not runs:
        return ("<div class=callnav><span class=callno>No fetches yet — run "
                "<code>jobhunt source</code></span></div>")

    def go(r, label, extra=None):
        params = {**base, "fetch": r, "page": 0}
        if extra:
            params.update(extra)
        return f"<a href='?{urlencode(params)}'>{label}</a>"

    if not cur:                                           # viewing all fetches
        return (f"<div class=callnav><span class=faint>&nbsp;</span>"
                f"<span class=callno><b>All fetches</b> &nbsp;·&nbsp; {len(runs)} runs</span>"
                f"{go(runs[0], f'latest fetch #{runs[0]} →')}</div>")
    idx = runs.index(cur)
    newer = runs[idx - 1] if idx > 0 else None            # runs sorted DESC
    older = runs[idx + 1] if idx + 1 < len(runs) else None
    latest = " · latest" if idx == 0 else ""

    def lnk(r, label):
        return f"<span class=faint>{label}</span>" if r is None else go(r, label)
    return (f"<div class=callnav>{lnk(older, '← earlier fetch')}"
            f"<span class=callno>Fetch #{cur}{latest} &nbsp;·&nbsp; {len(runs)} total"
            f" &nbsp; {go(0, 'all fetches', {'sort': ''})}</span>"
            f"{lnk(newer, 'later fetch →')}</div>")


def _run_nav(cur: int, runs: list, base: dict, view: str) -> str:
    """Always-on analysis-call bar for Apply-ready / Rejected. cur=0 = all calls;
    stepping into a call shows just what that call passed / filtered out."""
    from urllib.parse import urlencode
    what = "passed" if view == "apply" else "filtered out"
    if not runs:
        return (f"<div class=callnav><span class=callno>No analysis yet — run a call "
                f"from the <a href='/flow'>pipeline</a></span></div>")

    def go(r, label, extra=None):
        params = {**base, "view": view, "run": r, "page": 0}
        if extra:
            params.update(extra)
        return f"<a href='?{urlencode(params)}'>{label}</a>"

    if not cur:                                           # all calls
        return (f"<div class=callnav><span class=faint>&nbsp;</span>"
                f"<span class=callno><b>All calls</b> &nbsp;·&nbsp; {len(runs)} calls</span>"
                f"{go(runs[0], f'last call #{runs[0]} →')}</div>")
    idx = runs.index(cur)
    newer = runs[idx - 1] if idx > 0 else None
    older = runs[idx + 1] if idx + 1 < len(runs) else None
    latest = " · latest" if idx == 0 else ""

    def lnk(r, label):
        return f"<span class=faint>{label}</span>" if r is None else go(r, label)
    return (f"<div class=callnav>{lnk(older, '← earlier call')}"
            f"<span class=callno>Call #{cur}{latest} &middot; {what} &nbsp;·&nbsp; {len(runs)} total"
            f" &nbsp; {go(0, 'all calls')}</span>"
            f"{lnk(newer, 'later call →')}</div>")


def _filter_bar(base: dict, tier: str, ctype: str, locf: str, af: str, company: str,
                counts: dict | None, states) -> str:
    """Standalone tier/type/location/apply/company filters — for the card views
    (Apply-ready / Rejected) that have no table header to hang column menus on."""
    c = counts or {}
    tier_h = _hmenu("Tier", "tier", tier, [("", "All"), ("voice_speech", "Voice"),
                    ("ai_ml", "AI/ML"), ("swe_backend", "SWE")], base, c.get("tier"))
    type_h = _hmenu("Type", "ctype", ctype, [("", "All"), ("funded_startup", "Startup"),
                    ("unicorn", "Unicorn"), ("public_corp", "Public"),
                    ("staffing_proxy", "Staffing"), ("yc_early", "YC")], base, c.get("ctype"))
    loc_h = _hmenu("Location", "locf", locf,
                   [("", "All"), ("remote", "Remote"), ("hybrid", "Hybrid")]
                   + (states or []), base, c.get("locf"))
    apply_h = _hmenu("Apply", "af", af, [("", "All"), ("auto", "Auto"),
                     ("confirm", "Confirm"), ("manual", "Manual")], base, c.get("af"))
    comp_h = _search_menu("Company", "company", company, base)
    return (f"<div class=filterbar2>{tier_h}{type_h}{loc_h}{apply_h}{comp_h}</div>")


@app.get("/", response_class=HTMLResponse)
def index(tier: str = "", min_score: int = 40, fresh: int = 0, sort: str = "",
          view: str = "", min_fit: int = 50, page: int = 0, ctype: str = "",
          locf: str = "", af: str = "", company: str = "", run: int = 0,
          fetch: int = 0):
    return _render(tier, min_score, bool(fresh), sort, view=view, min_fit=min_fit,
                   page=max(0, page), ctype=ctype, locf=locf, af=af, company=company,
                   run=run, fetch=fetch)


@app.post("/resume", response_class=HTMLResponse)
async def resume_route(resume: str = Form(""), file: UploadFile = File(None)):
    from .core.config import resume_from_upload, save_resume
    if file is not None and file.filename:
        save_resume(resume_from_upload(file.filename, await file.read()))
    else:
        save_resume(resume)
    return _render("", 40, False, "", notice=(
        "Resume saved. Run <code>jobhunt analyze --force</code> to re-screen "
        "every job against it."))


@app.post("/prompt", response_class=HTMLResponse)
def prompt_route(prompt: str = Form("")):
    from .core.config import save_prompt
    save_prompt(prompt)
    return _render("", 40, False, "", notice=(
        "Prompt saved. Run <code>jobhunt analyze --force</code> to use it."))


@app.post("/love")
def love_route(company: str = Form(...)):
    from .core.favorites import toggle_loved
    return JSONResponse({"loved": toggle_loved(company)})


@app.post("/pin")
def pin_route(id: int = Form(...)):
    with db.connect() as conn:
        cur = conn.execute("SELECT pinned FROM jobs WHERE id = ?", [id]).fetchone()
        new = 0 if (cur and cur["pinned"]) else 1
        conn.execute("UPDATE jobs SET pinned = ? WHERE id = ?", [new, id])
    return JSONResponse({"pinned": bool(new)})


@app.post("/apply/{id}")
def apply_route(id: int):
    """Open a visible browser on this job's application form, pre-filled from
    your profile. You review + submit. Runs as a detached subprocess so the
    browser stays alive independent of this request."""
    import subprocess
    import sys
    from pathlib import Path
    with db.connect() as conn:
        r = conn.execute("SELECT url FROM jobs WHERE id = ?", [id]).fetchone()
    if not r or not r["url"] or r["url"] == "#":
        return JSONResponse({"ok": False, "error": "no apply URL"})
    root = Path(__file__).resolve().parents[1]          # .../aicode (has jobhunt pkg)
    subprocess.Popen([sys.executable, "-m", "jobhunt.apply.autofill", str(id)], cwd=str(root))
    return JSONResponse({"ok": True})


@app.post("/applied")
def applied_route(id: int = Form(...)):
    with db.connect() as conn:
        conn.execute("UPDATE jobs SET status = 'applied' WHERE id = ?", [id])
        n = conn.execute("UPDATE applications SET status = 'submitted', "
                         "submitted_at = CURRENT_TIMESTAMP "
                         "WHERE job_id = ? AND status = 'draft'", [id]).rowcount
        if not n:                                        # applied by hand, no draft
            conn.execute("INSERT INTO applications (job_id, status, submitted_at) "
                         "VALUES (?, 'submitted', CURRENT_TIMESTAMP)", [id])
    return JSONResponse({"ok": True})


@app.post("/dismiss")
def dismiss_route(id: int = Form(...)):
    with db.connect() as conn:
        conn.execute("UPDATE jobs SET status = 'closed' WHERE id = ?", [id])
    return JSONResponse({"ok": True})


@app.post("/add", response_class=HTMLResponse)
def add_route(url: str = Form(...)):
    from .cli import _fetch_favorite, _ingest
    from .core.favorites import add_favorite, parse_company_url

    entry = parse_company_url(url)
    if not entry:
        return _render("", 40, False, "", notice=(
            "<span class=nofit>Couldn’t detect an ATS</span> in that link — use a "
            "Greenhouse / Lever / Ashby / Workday careers URL."))
    label = entry.get("token") or entry.get("tenant")
    state = add_favorite(entry)
    raw = _fetch_favorite(entry)
    added = len(_ingest(raw, settings())) if raw else 0
    notice = (f"<b>{_e(entry['vendor'])}/{_e(label)}</b> {state} · "
              f"fetched {len(raw)} postings, <b>{added}</b> matched your filters.")
    return _render("", 40, False, "", notice=notice)


@app.post("/rank", response_class=HTMLResponse)
def rank_route(preference: str = Form(...), tier: str = Form(""),
               min_score: int = Form(40)):
    from .core.favorites import save_preference
    from .match.llm import claude_available, rank

    save_preference(preference)
    if claude_available():
        q = "SELECT id, title, company, location FROM jobs WHERE score >= ?"
        p: list = [min_score]
        if tier:
            q += " AND tier = ?"; p.append(tier)
        q += " ORDER BY score DESC LIMIT 60"
        with db.connect() as conn:
            jobs = [dict(r) for r in conn.execute(q, p).fetchall()]
        fits = rank(preference, jobs)
        if fits:
            with db.connect() as conn:
                for jid, f in fits.items():
                    conn.execute("UPDATE jobs SET fit = ? WHERE id = ?", [f, jid])
    return _render(tier, min_score, False, sort="fit", preference=preference)


@app.post("/check", response_class=HTMLResponse)
def check(url: str = Form(...), save: str = Form("")):
    from .apply.inspect import inspect

    cfg = settings()
    try:
        info = inspect(url)
    except Exception as e:
        banner = f"<div class=result><div class=nofit>Couldn’t fetch that URL</div><div class=kv>{_e(e)}</div></div>"
        return _page(_header() + _check_form(url) + banner)

    passes, remote = location_ok(info, cfg)
    info["remote"] = 1 if remote else 0
    score, tier = score_job(info, cfg)
    path = apply_path(classify_url(info["final_url"], info.get("source", "")))
    min_score = cfg["sourcing"]["min_score"]
    fits = passes and score >= min_score

    saved = ""
    if save and fits:
        info["score"], info["tier"] = score, tier
        with db.connect() as conn:
            state = db.upsert_job(conn, info)
        saved = f" · <span class=kv>saved ({state})</span>"

    verdict = ("<span class=fit-c>✅ fits your criteria</span>" if fits
               else "<span class=nofit>✕ doesn’t fit</span>")
    note = ("<div class=kv>no JSON-LD on page — title-only read; open the link to confirm.</div>"
            if info.get("_no_jsonld") else "")
    banner = (
        "<div class=result>"
        f"<div class=t>{_e(info['title']) or 'Untitled'}</div>"
        f"<div class=kv><b>{_e(info['company']) or '?'}</b> · {_e(info['location']) or 'location ?'}"
        f" · US-ok {passes} · remote {bool(remote)}</div>"
        f"<div class=kv>apply via <b>{path}</b>"
        f"{'  (auto-fillable ATS)' if path == 'auto' else ''} · "
        f"score <b>{score}</b> {_TIER_LABEL.get(tier, tier or '—')}</div>"
        f"<div class=kv><a href='{_e(info['final_url'])}' target=_blank rel=noopener>{_e(info['final_url'])}</a></div>"
        f"{note}<div class=verdict>{verdict}{saved}</div></div>"
    )
    return _page(_header() + _check_form() + banner)


def _flow_page(notice: str = "") -> str:
    from .core.config import companies, search_terms
    terms = search_terms()
    ncomp = sum(len(v or []) for v in companies().values())
    with db.connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs WHERE status != 'closed'").fetchone()[0]
        analyzed = conn.execute("SELECT COUNT(*) FROM jobs WHERE analysis IS NOT NULL AND status != 'closed'").fetchone()[0]
        ready = conn.execute("SELECT COUNT(*) FROM jobs WHERE (apply_ok = 1 OR pinned = 1) AND status != 'closed'").fetchone()[0]
        runs = conn.execute("SELECT COALESCE(MAX(analysis_run), 0) FROM jobs").fetchone()[0]
        fetch_report = _fetch_report(conn)
        call_report = _call_report(conn)
        pending = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {_PENDING_SQL}").fetchone()[0]
    top = ("<div class=flowtop><a href='/' class=brand>jobhunt</a>"
           "<a class=tool-btn href='/'>&larr; jobs</a></div>")
    banner = f"<div class=result style='margin-bottom:18px'>{notice}</div>" if notice else ""
    C = "<div class=fconn></div>"

    kw_rows = "".join(
        "<div class=kwrow>"
        f"<span class=kwname title=\"{_e(t)}\">{_e(t)}</span>"
        "<form method=post action='/keyword-remove' style='margin:0'>"
        f"<input type=hidden name=kw value=\"{_e(t)}\">"
        "<button class=kwrm type=submit title='remove'>&times;</button></form>"
        "</div>" for t in terms)
    kw_add = ("<form class=kwadd method=post action='/keyword-add'>"
              "<input type=text name=kw placeholder='Add a keyword…'>"
              "<button type=submit title='add'>+</button></form>")
    kw_node = ("<div class=fnode><div class=fhead><span class=fnum>1</span> Keywords &middot; JobSpy</div>"
               f"<div class=kwlist>{kw_rows}</div>{kw_add}</div>")
    co_node = ("<div class=fnode><div class=fhead><span class=fnum>1</span> Companies &middot; ATS</div>"
               f"<div class=fbig>{ncomp}</div>"
               "<div class=fdesc>Greenhouse / Lever / Ashby / Workday boards</div>"
               "<a class=fbtn href='/companies'>Manage &rarr;</a></div>")
    left = f"<div class=fcol>{kw_node}{co_node}</div>"
    merge = ("<svg class=fmerge viewBox='0 0 64 240' preserveAspectRatio=none aria-hidden=true>"
             "<path d='M0,58 C36,58 30,120 64,120'/>"
             "<path d='M0,182 C36,182 30,120 64,120'/></svg>")
    frep_block = (f"<div class=freplabel>per fetch &middot; newest first</div>{fetch_report}"
                  if fetch_report else "")
    fetch_node = ("<div class=fnode><div class=fhead><span class=fnum>2</span> Fetch &amp; store</div>"
                  f"<div class=fbig id=pcTotal>{total}</div><div class=fdesc>jobs scored &amp; deduped</div>"
                  "<form method=post action='/run-fetch' style='width:100%'>"
                  "<button style='width:100%'>&#9654; Run fetch</button></form>"
                  f"{frep_block}"
                  "<a class=fbtn href='/'>Show all &rarr;</a></div>")
    crep_block = (f"<div class=freplabel>per call &middot; newest first</div>{call_report}"
                  if call_report else "")
    pend_cls = "fpending on" if pending else "fpending"
    pend_txt = ("&#9889; <span id=pcPending>%d</span> jobs waiting &mdash; worth a call" % pending
                if pending else "&#10003; <span id=pcPending>0</span> &mdash; shortlist all screened")
    an_node = ("<div class=fnode><div class=fhead><span class=fnum>3</span> Analyze &middot; JD reader</div>"
               f"<div class=fbig id=pcAnalyzed>{analyzed}</div><div class=fdesc>read by Claude &middot; <span id=pcRuns>{runs}</span> call(s)</div>"
               f"<div class='{pend_cls}'>{pend_txt}</div>"
               "<form method=post action='/run-analyze' style='width:100%'>"
               "<button style='width:100%'>&#9654; Run call now</button></form>"
               f"{crep_block}</div>")
    ready_node = ("<div class='fnode ready'><div class=fhead><span class=fnum>4</span> Ready to apply</div>"
                  f"<div class=fbig id=pcReady>{ready}</div><div class=fdesc>vetted &amp; pinned jobs</div>"
                  "<a class=fbtn href='/?view=apply'>Show jobs &rarr;</a></div>")
    flow = ("<div class=flowcanvas><div class=flow>"
            + left + merge + fetch_node + C + an_node + C + ready_node
            + "</div></div>")
    poll = ("<script>setInterval(function(){fetch('/counts').then(function(r){return r.json();})"
            ".then(function(d){[['pcTotal',d.total],['pcAnalyzed',d.analyzed],['pcReady',d.ready],"
            "['pcRuns',d.runs],['pcPending',d.pending]].forEach(function(p){var e=document.getElementById(p[0]);"
            "if(e&&e.textContent!=String(p[1]))e.textContent=p[1];});}).catch(function(){});},4000);</script>")
    return _page(top + banner + flow + poll)


def _companies_page(notice: str = "") -> str:
    from .core.config import companies, company_board_url
    from .core.favorites import loved_companies
    comp = companies()
    loved = sorted(loved_companies())
    top = ("<div class=flowtop><a href='/' class=brand>jobhunt</a>"
           "<a class=tool-btn href='/flow'>&larr; pipeline</a></div>")
    banner = f"<div class=result style='margin-bottom:18px'>{notice}</div>" if notice else ""
    loved_section = ""
    if loved:
        chips = "".join(
            f"<span class=chip><a href='/?company={_e(c)}' style='color:inherit'>{_e(c)}</a>"
            f"<span class='love on chip-x' data-c=\"{_e(c)}\" onclick='love(this)'>&#9829;</span>"
            "</span>" for c in loved)
        loved_section = (f"<div class=panel><h2>Loved companies &nbsp;·&nbsp; {len(loved)}</h2>"
                         f"<div class=chips>{chips}</div></div>")
    add_form = ("<div class=panel><h2>Add a company</h2>"
                "<form class=row method=post action='/company-add'>"
                "<input class=url type=text name=url "
                "placeholder='Paste a careers link — Greenhouse / Lever / Ashby / Workday…'>"
                "<button type=submit>Add &amp; fetch</button></form></div>")
    rows = []
    for vendor in ("greenhouse", "lever", "ashby", "workday"):
        for tok in comp.get(vendor, []):
            name = tok.get("tenant") if isinstance(tok, dict) else tok
            rows.append(
                "<div class=corow>"
                f"<a class=coname href='{_e(company_board_url(vendor, tok))}' target=_blank "
                f"rel=noopener>{_e(name)}</a>"
                f"<span class=covendor>{vendor}</span>"
                "<form method=post action='/company-remove' style='margin:0;margin-left:auto'>"
                f"<input type=hidden name=vendor value='{vendor}'>"
                f"<input type=hidden name=token value=\"{_e(name)}\">"
                "<button class=corm type=submit title='remove'>&times;</button></form>"
                "</div>")
    body = ("<div class=panel><h2>ATS companies &nbsp;·&nbsp; "
            f"{len(rows)}</h2><div class=colist>" + "".join(rows) + "</div></div>")
    return _page(top + banner + loved_section + add_form + body)


@app.get("/companies", response_class=HTMLResponse)
def companies_route():
    return _companies_page()


@app.post("/company-add", response_class=HTMLResponse)
def company_add_route(url: str = Form("")):
    from .cli import _fetch_favorite, _ingest
    from .core.favorites import add_favorite, parse_company_url
    entry = parse_company_url(url)
    if not entry:
        return _companies_page("Couldn't detect an ATS from that link.")
    state = add_favorite(entry)
    raw = _fetch_favorite(entry)
    added = len(_ingest(raw, settings())) if raw else 0
    label = entry.get("token") or entry.get("tenant")
    return _companies_page(f"{entry['vendor']}/{label} {state} · {added} matching jobs added.")


@app.post("/company-remove", response_class=HTMLResponse)
def company_remove_route(vendor: str = Form(...), token: str = Form(...)):
    from .core.config import remove_company
    remove_company(vendor, token)
    return _companies_page(f"Removed {vendor}/{token}.")


def _bg(args: list):
    import subprocess
    import sys
    from pathlib import Path
    subprocess.Popen([sys.executable, "-m", "jobhunt.cli"] + args,
                     cwd=str(Path(__file__).resolve().parents[1]))


@app.get("/counts")
def counts_route():
    with db.connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs WHERE status != 'closed'").fetchone()[0]
        analyzed = conn.execute("SELECT COUNT(*) FROM jobs WHERE analysis IS NOT NULL AND status != 'closed'").fetchone()[0]
        ready = conn.execute("SELECT COUNT(*) FROM jobs WHERE (apply_ok = 1 OR pinned = 1) AND status != 'closed'").fetchone()[0]
        runs = conn.execute("SELECT COALESCE(MAX(analysis_run), 0) FROM jobs").fetchone()[0]
        pending = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {_PENDING_SQL}").fetchone()[0]
    return JSONResponse({"total": total, "analyzed": analyzed, "ready": ready,
                         "runs": runs, "pending": pending})


@app.get("/flow", response_class=HTMLResponse)
def flow_route():
    return _flow_page()


@app.post("/run-fetch", response_class=HTMLResponse)
def run_fetch_route():
    _bg(["source"])
    return _flow_page("Fetch started in the background — refresh in ~1–2 min for the new count.")


@app.post("/run-analyze", response_class=HTMLResponse)
def run_analyze_route():
    _bg(["analyze"])
    return _flow_page("Analyze call started — refresh in ~1–2 min; ‘ready to apply’ will fill in.")


@app.post("/keyword-add", response_class=HTMLResponse)
def keyword_add_route(kw: str = Form("")):
    from .core.config import add_keyword
    add_keyword(kw)
    return _flow_page()


@app.post("/keyword-remove", response_class=HTMLResponse)
def keyword_remove_route(kw: str = Form("")):
    from .core.config import remove_keyword
    remove_keyword(kw)
    return _flow_page()


def main():
    import uvicorn
    print("jobhunt UI  →  http://127.0.0.1:8765")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")


if __name__ == "__main__":
    main()
