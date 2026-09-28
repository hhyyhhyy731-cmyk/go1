// usage: node build.js blocks.json out.docx
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
  ShadingType, AlignmentType, BorderStyle, PageBreak, VerticalAlign, HeightRule,
} = require('docx');

const blocks = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const FONT = '맑은 고딕';
const MM = 56.7;                 // DXA per mm
const MARGIN = Math.round(15 * MM);
const W = Math.round(180 * MM);  // A4 210mm - 15mm x 2
const LABEL_W = Math.round(40 * MM);
const BLUE = 'DDEBF7';
const line = { style: BorderStyle.SINGLE, size: 4, color: '808080' };
const borders = { top: line, bottom: line, left: line, right: line };
const ALIGN = { center: AlignmentType.CENTER, right: AlignmentType.RIGHT };

const run = (t, f = {}) => new TextRun({
  text: t, font: FONT, size: Math.round((f.size || 10) * 2), bold: f.bold, italics: f.italic, color: f.color,
});
const para = (t, f = {}) => new Paragraph({
  alignment: ALIGN[f.align], spacing: { after: f.after ?? 40, before: f.before ?? 0 }, children: [run(t, f)],
});

function cell(spec, width) {
  const lines = spec.lines.map(l => (typeof l === 'string'
    ? para(l, { size: spec.size, bold: spec.bold, align: spec.align })
    : para(l.t, l)));
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, borders,
    verticalAlign: spec.top ? VerticalAlign.TOP : VerticalAlign.CENTER,
    shading: spec.fill ? { fill: spec.fill, type: ShadingType.CLEAR, color: 'auto' } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: lines.length ? lines : [para('')],
  });
}
function table(widths, rows, heights = []) {
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((cells, i) => new TableRow({
      height: heights[i] ? { value: Math.round(heights[i] * MM), rule: HeightRule.ATLEAST } : undefined,
      cantSplit: true,
      children: cells.map((c, j) => cell(c, widths[j])),
    })),
  });
}
function scale(ratios) {
  const sum = ratios.reduce((a, b) => a + b, 0);
  const ws = ratios.map(r => Math.floor(W * r / sum));
  ws[ws.length - 1] += W - ws.reduce((a, b) => a + b, 0);
  return ws;
}

const out = [];
for (const b of blocks) {
  switch (b.k) {
    case 'title':
      out.push(para(b.t, { bold: true, size: 16, align: 'center', after: 60 }));
      if (b.sub) out.push(para(b.sub, { size: 9, color: '555555', align: 'center', after: 100 }));
      break;
    case 'h': out.push(para(b.t, { bold: true, size: 12, before: 100, after: 40 })); break;
    case 'p': out.push(para(b.t, b)); break;
    case 'brk': out.push(new Paragraph({ children: [new PageBreak()] })); break;
    case 'name':
      out.push(table(scale([1, 1, 1.4]), [[
        { lines: ['1학년        반'] }, { lines: ['번호:'] }, { lines: ['이름:'] },
      ]], [10]));
      break;
    case 'form':
      out.push(table([LABEL_W, W - LABEL_W], b.rows.map(r => [
        { lines: r.label.split('\n'), fill: BLUE, bold: true, align: 'center' },
        { lines: r.guide ? [{ t: r.guide, size: 8, color: '7F7F7F', italic: true }] : [], top: true },
      ]), b.rows.map(r => r.h)));
      break;
    case 'grid': out.push(table(scale(b.widths), b.rows)); break;
    case 'lined': {
      const cw = Math.round(b.crit_w * MM), ws = [W - cw, cw];
      const thin = { style: BorderStyle.SINGLE, size: 4, color: 'A6A6A6' };
      const bd = { top: thin, bottom: thin, left: thin, right: thin };
      const mk = (kids, w, fill) => new TableCell({
        width: { size: w, type: WidthType.DXA }, borders: bd, verticalAlign: VerticalAlign.CENTER,
        shading: fill ? { fill, type: ShadingType.CLEAR, color: 'auto' } : undefined,
        margins: { top: 20, bottom: 20, left: 100, right: 100 }, children: kids,
      });
      const rows = [new TableRow({ children: [
        mk([para(b.head, { size: 8, color: '7F7F7F', italic: true })], ws[0], 'F2F2F2'),
        mk([para('기준', { size: 8, bold: true, align: 'center' })], ws[1], 'F2F2F2')] })];
      for (let i = 0; i < b.n; i++) rows.push(new TableRow({
        height: { value: Math.round(b.h * MM), rule: HeightRule.EXACT },
        children: [mk([para('')], ws[0]), mk([para('')], ws[1])] }));
      out.push(new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: ws, rows }));
      break;
    }
  }
}

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 20 } } } },
  sections: [{ properties: { page: { margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } }, children: out }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(process.argv[3], buf); console.log('docx written'); });
