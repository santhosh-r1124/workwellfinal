import React, { useState } from "react";

interface ImportResult {
  imported_rows: number;
  errors: string[];
}

export default function CSVImport() {
  const [file, setFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
      setError(null);
      setResult(null);
    }
  };

  const handleImport = async () => {
    if (!file) {
      setError("Please select a CSV/TSV file");
      return;
    }

    setImporting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/import/csv", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Import failed");
      }

      setResult(data);
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
      <h3 className="text-xl font-semibold text-white mb-4">Import Trainee Data</h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm text-slate-300 mb-2">
            Select CSV/TSV File
          </label>
          <input
            type="file"
            accept=".csv,.tsv"
            onChange={handleFileChange}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white"
          />
          {file && <p className="text-xs text-slate-400 mt-1">📁 {file.name}</p>}
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded p-3">
            <p className="text-red-300 text-sm">❌ {error}</p>
          </div>
        )}

        {result && (
          <div className="bg-green-900/30 border border-green-700 rounded p-3">
            <p className="text-green-300 text-sm font-semibold">
              ✅ Import Successful
            </p>
            <p className="text-green-300 text-xs mt-1">
              Imported {result.imported_rows} rows
            </p>
            {result.errors.length > 0 && (
              <details className="mt-2">
                <summary className="text-xs text-yellow-300 cursor-pointer">
                  {result.errors.length} error(s)
                </summary>
                <ul className="text-xs text-yellow-200 mt-2 space-y-1">
                  {result.errors.map((err, i) => (
                    <li key={i}>• {err}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}

        <button
          onClick={handleImport}
          disabled={!file || importing}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded font-semibold transition-colors"
        >
          {importing ? "Importing..." : "Import CSV"}
        </button>
      </div>
    </div>
  );
}
