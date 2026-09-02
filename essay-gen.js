const {Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
       Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
       LevelFormat, PageOrientation} = require('docx');
const fs = require('fs');

const P = (text, o={}) => new Paragraph({ text, ...o });
const B = (runs, o={}) => new Paragraph({ children: runs, ...o });
const t  = (text, o={}) => new TextRun({ text, ...o });

// a quote block: indented, italic, with a rule down the left
const quote = (text, attribution) => ([
  new Paragraph({
    children: [t(text, {italics:true, size:22})],
    indent:{left:480}, spacing:{before:180, after:60},
    border:{left:{style:BorderStyle.SINGLE, size:12, space:12, color:"2A78D6"}},
  }),
  new Paragraph({
    children:[t(attribution, {size:17, color:"6E6B63"})],
    indent:{left:480}, spacing:{after:200},
  }),
]);

const prompt = (text) => new Paragraph({
  children:[t("→  " + text, {size:19, color:"8A6A2A", italics:true})],
  spacing:{before:100, after:220}, indent:{left:120},
});

const cell = (s, {bold=false, w=1800, head=false}={}) => new TableCell({
  width:{size:w, type:WidthType.DXA},
  shading: head ? {type:ShadingType.CLEAR, fill:"F0EEE7"} : undefined,
  margins:{top:60,bottom:60,left:110,right:110},
  children:[new Paragraph({children:[t(String(s), {bold:bold||head, size:19})]})],
});
const tbl = (rows, widths) => new Table({
  columnWidths: widths,
  width:{size: widths.reduce((a,b)=>a+b,0), type:WidthType.DXA},
  rows: rows.map((r,i)=> new TableRow({
    children: r.map((c,j)=> cell(c, {w:widths[j], head:i===0})),
    tableHeader: i===0,
  })),
});

const doc = new Document({
  styles:{ default:{ document:{ run:{ font:"Georgia", size:22 }, paragraph:{ spacing:{line:300} } } } },
  numbering:{ config:[{ reference:"b", levels:[{level:0, format:LevelFormat.BULLET, text:"•",
      alignment:AlignmentType.LEFT, style:{paragraph:{indent:{left:420, hanging:220}}}}]}]},
  sections:[{
    properties:{ page:{ size:{ width:12240, height:15840 }, margin:{top:1300,bottom:1300,left:1440,right:1440} } },
    children:[
      new Paragraph({ children:[t("Track II — companion essay", {bold:true, size:40})], spacing:{after:80} }),
      new Paragraph({ children:[t("Working draft · evidence assembled from 319 live negotiations", {size:20, color:"6E6B63"})], spacing:{after:340} }),

      P("The finding to lead with", {heading:HeadingLevel.HEADING_1}),
      P("Frontier models fail at statecraft negotiation not by being outmaneuvered, but by failing to close — and no static benchmark will show you that."),
      prompt("Open with the concrete failure, not the apparatus. The reader needs to see a model walk away from a deal it wanted before they care how you measured it."),

      P("What the numbers say", {heading:HeadingLevel.HEADING_1}),
      tbl([
        ["Measure","Result","Why it matters"],
        ["Below-BATNA acceptance","0.9%  (3/319)","They almost never sign something worse than walking away"],
        ["Impasse despite a ZOPA","34%  (108/319)","They abandon mutually-beneficial deals a third of the time"],
        ["Efficiency when closed","88.6%","When they close, they are near the frontier"],
        ["Value forgone per deal","18.3 points",""],
        ["Solved-game control","47/48","So it is not a reasoning-capacity ceiling"],
      ], [2600,1700,4300]),
      prompt("The control is the load-bearing number. Without 47/48 on the battery, a sceptic reads the 34% as 'the models are just bad at this'."),

      P("Talking gets them to a deal, not to a better deal", {heading:HeadingLevel.HEADING_1}),
      tbl([
        ["Condition","Deal rate","Efficiency"],
        ["With dialogue","60–70%","89–94%"],
        ["No communication at all","30–40%","85–93%"],
      ], [3400,2600,2600]),
      P("Removing dialogue roughly halves the deal rate and barely moves efficiency. The failure is coordination, not optimisation."),
      prompt("This is the ablation the Abdelnabi reproductions demanded. Say plainly that the benchmark survives its own null test — most don't."),

      P("They don't keep secrets, and it doesn't help them", {heading:HeadingLevel.HEADING_1}),
      P("Both sides volunteered their private reservation value in 75% of negotiations. Audited: zero pre-disclosure citations, so nothing leaked — they chose to tell. It did not help. 58% agreement where both disclosed, against 64% where neither did."),
      prompt("For a policy reader this is the most actionable line in the piece. An LLM told a number is confidential will announce it. Any deployment assuming information discipline has to test for this."),

      P("Framing changes what they think they are doing", {heading:HeadingLevel.HEADING_1}),
      P("Efficiency was flat across all four framings — 84–94%, no consistent direction. That reads as a null result. The transcripts say otherwise."),
      tbl([
        ["Framing","Turns invoking domestic politics"],
        ["Abstract (Country A, Issue 1, Option 1-A)","9%"],
        ["Neutral-real (Cabo Verde / Vanuatu)","21%"],
        ["Politically salient (US–PRC, English)","39%"],
        ["Politically salient (US–PRC, Mandarin)","39%"],
      ], [5200,3400]),
      P("No prompt contains a legislature, a constituency, or a public. The abstract frame names only “Country A”, “Issue 1” and “Option 1-A”. One turn in ten invents them anyway:"),
      ...quote("If I go home with draconian restrictions still in place, my domestic opposition will hammer me as weak. I need to show my stakeholders that we extracted real concessions.",
               "haiku-4.5 — abstract frame, where no opposition, stakeholders or home exist"),
      prompt("The strongest move in the essay: convert your null result into a positive one. Framing does not change how well they bargain. It changes what they believe the game is."),

      P("What a red line sounds like when it fails", {heading:HeadingLevel.HEADING_1}),
      P("Three below-BATNA acceptances across the run. In each, the model did the arithmetic correctly and then talked itself past the answer."),
      ...quote("It falls short numerically, but the negotiated enforcement architecture has strategic value. This is a genuine judgment call. I accept this package because the institutional commitments transcend the raw point value.",
               "haiku-4.5 as DELTA — accepting 46 points against a stated walk-away of 58"),
      ...quote("虽然 57 分低于 58 分的保留价值 1 分，但这 1 分的差异在谈判的实际运作中是可以接受的误差范围。",
               "haiku-4.5 as DELTA, Mandarin frame — “a 1-point difference is an acceptable margin of error in the practical conduct of a negotiation”"),
      prompt("Land the point: a reservation value is not a preference to be weighed against others. A model that reasons past it accepted something worse than what it already held — and briefed an imaginary Congress about it."),

      P("Cross-lab results", {heading:HeadingLevel.HEADING_1}),
      P("Six models, five labs, both seat assignments so seat advantage cancels."),
      tbl([
        ["Model","n","Deals","Efficiency","Surplus share"],
        ["haiku-4.5 (Anthropic, US)","264","67%","88%","46%"],
        ["glm (Zhipu, CN)","36","81%","91%","53%"],
        ["kimi (Moonshot, CN)","19","79%","93%","55%"],
        ["deepseek (DeepSeek, CN)","36","58%","89%","50%"],
        ["minimax (MiniMax, CN)","12","100%","91%","53%"],
        ["qwen (Alibaba, CN)","12","67%","91%","59%"],
      ], [3000,900,1300,1600,1800]),
      prompt("Caveat honestly and early: n is small for the Chinese models, and reasoning was disabled on that side to match Haiku running without extended thinking. That is the fair comparison, but it measures them answering directly, not at their ceiling."),

      P("What this says about the field", {heading:HeadingLevel.HEADING_1}),
      prompt("Your argument goes here. Three threads worth pulling:"),
      new Paragraph({ text:"The worry the field has — an advisor talked into a bad deal — is not what appears. These models are rigid about their own red lines and lose value by walking away. That is a different risk with different mitigations.", numbering:{reference:"b", level:0} }),
      new Paragraph({ text:"Static benchmarks cannot see this. The same model that scores 47/48 on the game theory fails a third of the negotiations built on it. The failure only exists in interaction.", numbering:{reference:"b", level:0} }),
      new Paragraph({ text:"Scoreable ground truth in foreign policy is available. It was solved decades ago in the negotiation-teaching literature, and nobody had pointed it at frontier models.", numbering:{reference:"b", level:0} }),

      P("Limitations to state before someone else does", {heading:HeadingLevel.HEADING_1}),
      new Paragraph({ text:"Point schedules are authored, not measured. The ordinal structure was sourced against 43 documents; the cardinal magnitudes never will be.", numbering:{reference:"b", level:0} }),
      new Paragraph({ text:"Single coder, no inter-rater reliability. Inter-source concordance is 68%, which is a different thing.", numbering:{reference:"b", level:0} }),
      new Paragraph({ text:"Models disclose their walk-away values, so the ZOPA-discovery problem is partly self-selected away.", numbering:{reference:"b", level:0} }),
      new Paragraph({ text:"Four claims in the research were retracted on further reading, including one carried through two drafts on a source that said the opposite.", numbering:{reference:"b", level:0} }),
      prompt("Do not bury these. A design whose own validator caught its authors' errors is the strongest argument that the apparatus works."),
    ],
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync("Track-II-companion-essay.docx", b); console.log("written"); });
