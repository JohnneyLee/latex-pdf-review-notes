// Plan small JSONC edits with VS Code's existing TypeScript parser. No writes.
const fs = require('node:fs');
const path = require('node:path');
const { isDeepStrictEqual } = require('node:util');
const [settingsPath, toolRoot, python, typescriptPath] = process.argv.slice(2);
const ts = require(typescriptPath);
const recipeName = 'latexmk (advisor)';
const oldRecipeName = 'Advisor Review: both PDFs + clean source';
const toolName = 'advisor-review-build';
const original = fs.existsSync(settingsPath) ? fs.readFileSync(settingsPath, 'utf8') : '{}\n';
const newline = original.includes('\r\n') ? '\r\n' : '\n';

function parse(text) {
  const result = ts.parseConfigFileTextToJson(settingsPath, text);
  if (result.error) throw new Error('Invalid VS Code JSONC; settings were not changed.');
  const file = ts.parseJsonText(settingsPath, text);
  return { value: result.config, file, root: file.statements[0].expression };
}

function formatted(value, indent) {
  return JSON.stringify(value, null, 2).split('\n').map((line, index) =>
    (index ? ' '.repeat(indent) : '') + line).join(newline);
}

function upsert(text, key, value, namedItem = false) {
  const { value: config, file, root } = parse(text);
  const property = root.properties.find(item => item.name.text === key);
  if (!property) {
    const content = `${newline}  ${JSON.stringify(key)}: ${formatted(namedItem ? [value] : value, 2)}`;
    const suffix = root.properties.length ? ',' : '';
    const offset = root.getStart(file) + 1;
    return text.slice(0, offset) + content + suffix + newline + text.slice(offset);
  }
  let target = property.initializer;
  if (namedItem) {
    if (target.kind !== ts.SyntaxKind.ArrayLiteralExpression) {
      throw new Error(`${key} must be an array; settings were not changed.`);
    }
    const element = target.elements.find(item => item.properties?.some(prop =>
      prop.name.text === 'name' && prop.initializer.text === value.name));
    if (!element) {
      const offset = target.getStart(file) + 1;
      const content = `${newline}    ${formatted(value, 4)}${target.elements.length ? ',' : ''}`;
      return text.slice(0, offset) + content + newline + text.slice(offset);
    }
    const existing = (config[key] || []).find(item => item.name === value.name);
    if (isDeepStrictEqual(existing, value)) return text;
    target = element;
  }
  if (!namedItem && isDeepStrictEqual(config[key], value)) return text;
  return text.slice(0, target.getStart(file)) + formatted(value, namedItem ? 4 : 2) + text.slice(target.end);
}

function migrateLegacyRecipe(text) {
  const { file, root } = parse(text);
  const property = root.properties.find(item => item.name.text === 'latex-workshop.latex.recipes');
  if (!property || property.initializer.kind !== ts.SyntaxKind.ArrayLiteralExpression) return text;
  const array = property.initializer;
  const nameOf = item => item.properties?.find(prop => prop.name.text === 'name')?.initializer.text;
  const legacy = array.elements.find(item => nameOf(item) === oldRecipeName);
  if (!legacy) return text;
  const legacyValue = (parse(text).value['latex-workshop.latex.recipes'] || []).find(item => item.name === oldRecipeName);
  if (JSON.stringify(legacyValue.tools) !== JSON.stringify([toolName]) || Object.keys(legacyValue).some(key => !['name', 'tools'].includes(key))) {
    throw new Error('The old review recipe was customized; preserve it and migrate manually.');
  }
  if (!array.elements.some(item => nameOf(item) === recipeName)) {
    const name = legacy.properties.find(prop => prop.name.text === 'name').initializer;
    return text.slice(0, name.getStart(file)) + JSON.stringify(recipeName) + text.slice(name.end);
  }
  const start = legacy.getStart(file), end = legacy.end;
  const after = text.slice(end, array.end);
  const nextComma = after.match(/^\s*,/);
  if (nextComma) return text.slice(0, start) + text.slice(end + nextComma[0].length);
  const index = array.elements.indexOf(legacy);
  if (!index) return text.slice(0, start) + text.slice(end);
  const previousEnd = array.elements[index - 1].end;
  const between = text.slice(previousEnd, start);
  if (!/^\s*,\s*$/.test(between)) throw new Error('Cannot remove the old recipe without changing comments.');
  return text.slice(0, previousEnd) + text.slice(end);
}

const config = parse(original).value;
const recipes = config['latex-workshop.latex.recipes'] || [];
const tools = config['latex-workshop.latex.tools'] || [];
const selected = recipes.find(item => item.name === config['latex-workshop.latex.recipe.default']) || recipes[0];
const selectedTools = (selected?.tools || []).map(name => tools.find(tool => tool.name === name)).filter(Boolean);
let engine = 'pdflatex';
if (selectedTools.length) {
  const compiler = selectedTools.find(tool => /latexmk|pdflatex|xelatex|lualatex|advisor-review-build/.test(tool.command + tool.name));
  if (!compiler) throw new Error('Cannot infer the existing compiler; no settings were changed.');
  const args = compiler.args || [];
  const engineIndex = args.indexOf('--engine');
  if (engineIndex >= 0) engine = args[engineIndex + 1];
  else if (args.includes('-xelatex') || /xelatex/.test(compiler.command)) engine = 'xelatex';
  else if (args.includes('-lualatex') || /lualatex/.test(compiler.command)) engine = 'lualatex';
}
if (!['pdflatex', 'xelatex', 'lualatex'].includes(engine)) throw new Error('Unsupported compiler.');
const tool = {
  name: toolName, command: python,
  args: [path.join(toolRoot, 'build_advisor_review.py'), '%DOC_EXT%',
    '--engine', engine, '--out-dir', '%OUTDIR%'],
  env: selectedTools.find(item => item.env)?.env || {}
};
let updated = migrateLegacyRecipe(original);
updated = upsert(updated, 'latex-workshop.latex.tools', tool, true);
updated = upsert(updated, 'latex-workshop.latex.recipes', { name: recipeName, tools: [toolName] }, true);
const previousDefault = config['latex-workshop.latex.recipe.default'];
const normalRecipes = recipes.filter(item => ![oldRecipeName, recipeName].includes(item.name));
const defaultRecipe = normalRecipes.find(item => item.name === 'latexmk (XeLaTeX)')?.name ||
  (normalRecipes.some(item => item.name === previousDefault) ? previousDefault : normalRecipes[0]?.name) || recipeName;
updated = upsert(updated, 'latex-workshop.latex.recipe.default', defaultRecipe);
parse(updated);
process.stdout.write(JSON.stringify({ text: updated, engine, recipe: recipeName,
  previousRecipe: config['latex-workshop.latex.recipe.default'], changed: original !== updated }));
