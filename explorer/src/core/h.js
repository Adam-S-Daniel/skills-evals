/* A tiny node tree: the page is built as plain objects, then turned  */
/* into DOM with createElement and text nodes only, never HTML text. */
import { githubLink } from './format.js';

export const SVG_TAGS = new Set(['svg', 'g', 'rect', 'line', 'circle', 'path', 'text', 'polyline']);

export function h(tag, attrs) {
  const kids = [];
  const push = (c) => {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) c.forEach(push);
    else kids.push(typeof c === 'object' ? c : String(c));
  };
  for (let i = 2; i < arguments.length; i++) push(arguments[i]);
  return { tag: tag, attrs: attrs || {}, children: kids };
}

export function link(url, text) {
  const ok = githubLink(url);
  if (!ok) return null;
  return h('a', { href: ok, rel: 'noopener', target: '_blank' }, text);
}

export const VISIBLE_ATTRS = ['title', 'aria-label', 'data-tip'];

export function textOf(node) {
  if (node === null || node === undefined) return '';
  if (typeof node === 'string') return node;
  let s = '';
  for (const k of VISIBLE_ATTRS) if (node.attrs && typeof node.attrs[k] === 'string') s += ' ' + node.attrs[k] + ' ';
  for (const c of node.children) s += textOf(c) + ' ';
  return s;
}

export function findAll(node, pred, out) {
  out = out || [];
  if (node && typeof node === 'object') {
    if (pred(node)) out.push(node);
    node.children.forEach((c) => findAll(c, pred, out));
  }
  return out;
}

export function toDom(node, doc) {
  if (typeof node === 'string') return doc.createTextNode(node);
  const isSvg = SVG_TAGS.has(node.tag);
  const el = isSvg ? doc.createElementNS('http://www.w3.org/2000/svg', node.tag) : doc.createElement(node.tag);
  for (const k of Object.keys(node.attrs)) {
    const v = node.attrs[k];
    if (typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined && v !== false) el.setAttribute(k, String(v));
  }
  for (const c of node.children) el.appendChild(toDom(c, doc));
  return el;
}
