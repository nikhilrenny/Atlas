import { useState } from "react";

const API = "http://127.0.0.1:8765/api";

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(",")[1]); // strip the data: prefix
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function InputField({ field, value, onChange }) {
  if (field.type === "file") {
    return (
      <label className="tb-field">
        <span>{field.label}</span>
        <input
          type="file"
          accept="image/*"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (file) onChange(await fileToBase64(file));
          }}
        />
      </label>
    );
  }
  if (field.type === "boolean") {
    return (
      <label className="tb-field">
        <span>{field.label}</span>
        <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} />
      </label>
    );
  }
  if (field.type === "select") {
    return (
      <label className="tb-field">
        <span>{field.label}</span>
        <select value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
          <option value="" disabled>choose...</option>
          {(field.options || []).map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      </label>
    );
  }
  return (
    <label className="tb-field">
      <span>{field.label}</span>
      <input
        type={field.type === "number" ? "number" : "text"}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        required={field.required}
      />
    </label>
  );
}

function OutputPanel({ outputType, data }) {
  if (data == null) return null;
  if (outputType === "image") {
    const mimeMatch = /^data:image\/(\w+);base64,/.exec(data);
    const ext = mimeMatch ? mimeMatch[1] : "png";
    return (
      <div className="tb-image-output">
        <img src={data} alt="tool output" style={{ maxWidth: "100%" }} />
        <a className="tb-download" href={data} download={`output.${ext}`}>download {ext}</a>
      </div>
    );
  }
  if (outputType === "table" && data?.columns && data?.rows) {
    return (
      <table className="tb-table">
        <thead><tr>{data.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {data.rows.map((row, i) => (
            <tr key={i}>{row.map((cell, j) => <td key={j}>{String(cell)}</td>)}</tr>
          ))}
        </tbody>
      </table>
    );
  }
  if (outputType === "json") {
    return <pre className="tb-json">{JSON.stringify(data, null, 2)}</pre>;
  }
  return <p className="tb-text">{String(data)}</p>;
}

export { OutputPanel };

export default function ToolPanel({ manifest, onDelete, onTogglePin }) {
  const [values, setValues] = useState(() =>
    Object.fromEntries(manifest.inputs.filter((f) => f.default != null).map((f) => [f.name, f.default]))
  );
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const setField = (name, val) => setValues((v) => ({ ...v, [name]: val }));

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API}/toolbuilder/tools/${manifest.id}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inputs: values }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "tool run failed");
      setResult(body);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tool-panel">
      <div className="tb-header">
        <h3>{manifest.name}</h3>
        <div className="tb-header-actions">
          {onTogglePin && (
            <button className="tb-pin" onClick={() => onTogglePin(manifest.id, !manifest.pinned)}>
              {manifest.pinned ? "unpin" : "pin"}
            </button>
          )}
          {onDelete && <button className="tb-delete" onClick={() => onDelete(manifest.id)}>delete</button>}
        </div>
      </div>
      <p className="tb-desc">{manifest.description}</p>
      {manifest.source_url && <p className="tb-source">source: {manifest.source_url}</p>}

      <div className="tb-fields">
        {manifest.inputs.map((field) => (
          <InputField key={field.name} field={field} value={values[field.name]} onChange={(v) => setField(field.name, v)} />
        ))}
      </div>

      <button className="tb-run" onClick={run} disabled={loading}>
        {loading ? "Running..." : "Run"}
      </button>

      {error && <p className="tb-error">{error}</p>}
      {result && <OutputPanel outputType={result.output_type} data={result.data} />}
    </div>
  );
}
