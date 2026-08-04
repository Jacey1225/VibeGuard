/** Heuristic language guess for pasted code, used to label the composer input. */
export function detectLanguage(code: string): string {
  const t = code.trim();
  if (!t) return "";
  if (/^\s*[{[]/.test(t) && /"\s*:/.test(t)) return "JSON";
  if (/\b(def |import (os|sys)|print\()/.test(t)) return "Python";
  if (/\b(SELECT|INSERT INTO|CREATE TABLE)\b/i.test(t)) return "SQL";
  if (/<\/?[a-z][\s\S]*>/i.test(t) && !/=>/.test(t)) return "HTML";
  if (/\b(interface |type \w+ =|: string|: number)\b/.test(t)) return "TypeScript";
  if (/\b(const |let |function |=>|require\(|import )/.test(t)) return "JavaScript";
  return "Code";
}
