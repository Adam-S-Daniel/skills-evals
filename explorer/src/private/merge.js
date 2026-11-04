/* Private-skill results (dataset explorer_private, the same schema as the
   public document) merged into the public document, each subject marked
   private so its card carries a "Private" badge. Absent: nothing changes. */
export function mergePrivate(doc, priv) {
  if (!priv || typeof priv !== 'object' || !Array.isArray(priv.skills)) return doc;
  const out = Object.assign({}, doc);
  const mark = (s) => Object.assign({}, s, { private: true });
  out.skills = (Array.isArray(doc.skills) ? doc.skills : []).concat(priv.skills.filter(Boolean).map(mark));
  const pe = priv.evals && typeof priv.evals === 'object' ? priv.evals : null;
  if (pe) {
    const e = Object.assign({ runs: [], bare_runs: [] }, doc.evals || {});
    out.evals = Object.assign({}, e, {
      runs: (e.runs || []).concat(Array.isArray(pe.runs) ? pe.runs : []),
      bare_runs: (e.bare_runs || []).concat(Array.isArray(pe.bare_runs) ? pe.bare_runs : [])
    });
  }
  return out;
}
