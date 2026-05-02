import { useEffect, useMemo, useState } from "react";
import api from "../services/api";

function DataImport() {
  const [customersFile, setCustomersFile] = useState(null);
  const [ordersFile, setOrdersFile] = useState(null);
  const [signalsFile, setSignalsFile] = useState(null);

  const [customersResult, setCustomersResult] = useState(null);
  const [ordersResult, setOrdersResult] = useState(null);
  const [signalsResult, setSignalsResult] = useState(null);

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [loadingType, setLoadingType] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetchImportHistory();
  }, []);

  const fetchImportHistory = async () => {
    try {
      setHistoryLoading(true);
      setError("");

      const response = await api.get("/imports/history");
      setHistory(response.data || []);
    } catch (error) {
      console.error("Error fetching import history:", error);
      setHistory([]);
      setError("Could not load import history. Make sure the backend is running.");
    } finally {
      setHistoryLoading(false);
    }
  };

  const uploadStandardFile = async (type, file, setResult) => {
    if (!file) {
      setResult({
        error: "Please select a CSV file first.",
      });
      return;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setResult({
        error: "Only CSV files are allowed.",
      });
      return;
    }

    try {
      setLoadingType(type);
      setError("");

      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post(`/imports/${type}`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setResult(response.data);
      await fetchImportHistory();
    } catch (error) {
      console.error(`Error uploading ${type}:`, error);

      setResult({
        error:
          error?.response?.data?.detail ||
          `Failed to upload ${type} CSV. Please check the file format.`,
      });
    } finally {
      setLoadingType("");
    }
  };

  const uploadSignalsFile = async () => {
    if (!signalsFile) {
      setSignalsResult({
        error: "Please select a CSV file first.",
      });
      return;
    }

    if (!signalsFile.name.toLowerCase().endsWith(".csv")) {
      setSignalsResult({
        error: "Only CSV files are allowed.",
      });
      return;
    }

    try {
      setLoadingType("signals");
      setError("");

      const formData = new FormData();
      formData.append("file", signalsFile);

      const response = await api.post("/social-listener/import-csv", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setSignalsResult(response.data);
      await fetchImportHistory();
    } catch (error) {
      console.error("Error uploading signals:", error);

      setSignalsResult({
        error:
          error?.response?.data?.detail ||
          "Failed to upload signals CSV. Please check the file format.",
      });
    } finally {
      setLoadingType("");
    }
  };

  const clearResults = () => {
    setCustomersResult(null);
    setOrdersResult(null);
    setSignalsResult(null);
    setError("");
  };

  const historyStats = useMemo(() => {
    const total = history.length;
    const success = history.filter((item) => item.status === "success").length;
    const partial = history.filter(
      (item) => item.status === "partial_success"
    ).length;
    const failed = history.filter((item) => item.status === "failed").length;

    const inserted = history.reduce(
      (sum, item) => sum + Number(item.inserted_count || 0),
      0
    );

    const skipped = history.reduce(
      (sum, item) => sum + Number(item.skipped_count || 0),
      0
    );

    const errors = history.reduce(
      (sum, item) => sum + Number(item.error_count || 0),
      0
    );

    return {
      total,
      success,
      partial,
      failed,
      inserted,
      skipped,
      errors,
    };
  }, [history]);

  const latestImport = history[0] || null;

  const getStatusBadgeClass = (status) => {
    if (status === "success") return "badge badge-green";
    if (status === "partial_success") return "badge badge-yellow";
    return "badge badge-red";
  };

  const getEntityBadgeClass = (entity) => {
    if (entity === "customers") return "badge badge-blue";
    if (entity === "orders") return "badge badge-green";
    if (entity === "signals") return "badge badge-purple";
    if (entity === "customer_signals") return "badge badge-purple";
    return "badge badge-yellow";
  };

  const formatEntityLabel = (entity) => {
    const labels = {
      customers: "Customers",
      orders: "Orders",
      notes: "Notes",
      signals: "Signals",
      customer_signals: "Customer Signals",
    };

    return labels[entity] || entity || "Unknown";
  };

  const formatDate = (value) => {
    if (!value) return "-";
    return new Date(value).toLocaleString();
  };

  const formatFileSize = (file) => {
    if (!file) return "";

    const sizeKb = file.size / 1024;

    if (sizeKb < 1024) {
      return `${sizeKb.toFixed(1)} KB`;
    }

    return `${(sizeKb / 1024).toFixed(2)} MB`;
  };

  const renderCsvRequirements = (title, columns, exampleRows) => {
    return (
      <div className="summary-box">
        <p className="summary-text">
          <strong>{title}</strong>
        </p>

        <p className="summary-note">
          Required columns:
        </p>

        <div className="btn-row" style={{ marginTop: 10 }}>
          {columns.map((column) => (
            <span key={column} className="badge badge-blue">
              {column}
            </span>
          ))}
        </div>

        <div style={{ marginTop: 14 }}>
          <p className="summary-note">
            Example:
          </p>

          <div className="table-wrap">
            <table className="table" style={{ minWidth: 520 }}>
              <thead>
                <tr>
                  {columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {exampleRows.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {columns.map((column) => (
                      <td key={column}>{row[column]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  const renderSelectedFile = (file) => {
    if (!file) {
      return <p className="summary-note">No file selected yet.</p>;
    }

    return (
      <div className="summary-box" style={{ marginTop: 12 }}>
        <p className="summary-text">
          <strong>{file.name}</strong>
        </p>
        <p className="summary-note">
          Size: {formatFileSize(file)}
        </p>
      </div>
    );
  };

  const renderResult = (result) => {
    if (!result) return null;

    if (result.error) {
      return (
        <div className="error-state" style={{ marginTop: 14 }}>
          <strong>Error:</strong> {result.error}
        </div>
      );
    }

    return (
      <div className="summary-box" style={{ marginTop: 14 }}>
        <div className="results-bar">
          <p className="summary-text">
            <strong>Import Result</strong>
          </p>

          <span className={getStatusBadgeClass(result.status)}>
            {result.status || "unknown"}
          </span>
        </div>

        <div className="grid-3" style={{ marginTop: 14 }}>
          <div className="stat-box">
            <p className="stat-label">Entity</p>
            <p className="stat-value" style={{ fontSize: 20 }}>
              {formatEntityLabel(result.entity)}
            </p>
          </div>

          <div className="stat-box">
            <p className="stat-label">Inserted</p>
            <p className="stat-value">{result.inserted ?? 0}</p>
          </div>

          <div className="stat-box">
            <p className="stat-label">Skipped</p>
            <p className="stat-value">{result.skipped ?? 0}</p>
          </div>
        </div>

        <div className="kv-list" style={{ marginTop: 14 }}>
          <div className="kv-row">
            <span className="kv-key">File</span>
            <span className="kv-value">{result.file_name || "-"}</span>
          </div>

          <div className="kv-row">
            <span className="kv-key">Log ID</span>
            <span className="kv-value">
              {result.log_id ? `#${result.log_id}` : "-"}
            </span>
          </div>

          <div className="kv-row">
            <span className="kv-key">Imported At</span>
            <span className="kv-value">{formatDate(result.imported_at)}</span>
          </div>

          {result.created_actions !== undefined && (
            <div className="kv-row">
              <span className="kv-key">Created Actions</span>
              <span className="kv-value">{result.created_actions}</span>
            </div>
          )}

          {result.matched_customers !== undefined && (
            <div className="kv-row">
              <span className="kv-key">Matched Customers</span>
              <span className="kv-value">{result.matched_customers}</span>
            </div>
          )}

          {result.unmatched_signals !== undefined && (
            <div className="kv-row">
              <span className="kv-key">Unmatched Signals</span>
              <span className="kv-value">{result.unmatched_signals}</span>
            </div>
          )}
        </div>

        {result.errors?.length > 0 && (
          <div className="error-state" style={{ marginTop: 14 }}>
            <strong>Rows skipped / errors:</strong>
            <ul className="error-list">
              {result.errors.slice(0, 8).map((err, index) => (
                <li key={index}>{err}</li>
              ))}
            </ul>

            {result.errors.length > 8 && (
              <p className="summary-note">
                Showing first 8 errors out of {result.errors.length}.
              </p>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderImportCard = ({
    step,
    title,
    subtitle,
    file,
    setFile,
    result,
    onUpload,
    loadingKey,
    accentBadge,
  }) => {
    const isLoading = loadingType === loadingKey;

    return (
      <div className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">Step {step}</p>
            <h2 className="section-title">{title}</h2>
            <p className="section-description">{subtitle}</p>
          </div>

          <span className={accentBadge}>{title}</span>
        </div>

        <input
          className="input"
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />

        {renderSelectedFile(file)}

        <div className="btn-row" style={{ marginTop: 14 }}>
          <button
            className="btn btn-primary"
            onClick={onUpload}
            disabled={isLoading}
          >
            {isLoading ? "Uploading..." : `Upload ${title}`}
          </button>
        </div>

        {renderResult(result)}
      </div>
    );
  };

  return (
    <div className="page">
      <section className="page-hero">
        <div>
          <p className="page-eyebrow">Data Pipeline</p>
          <h1 className="page-title">Data Import</h1>
          <p className="page-subtitle">
            Import customers, revenue history, and real-world customer signals.
            Signals are analyzed by AI and can automatically create prioritized
            business actions.
          </p>
        </div>

        <div className="hero-actions">
          <button className="btn btn-secondary" onClick={fetchImportHistory}>
            Refresh History
          </button>

          <button className="btn btn-secondary" onClick={clearResults}>
            Clear Results
          </button>
        </div>
      </section>

      {error && <div className="error-state">{error}</div>}

      <section className="grid-4">
        <div className="metric-card">
          <p className="metric-label">Import Runs</p>
          <p className="metric-value">{historyStats.total}</p>
          <p className="metric-meta">Total CSV import operations</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Inserted Records</p>
          <p className="metric-value">{historyStats.inserted}</p>
          <p className="metric-meta">Records successfully added</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Skipped Records</p>
          <p className="metric-value">{historyStats.skipped}</p>
          <p className="metric-meta">Rows skipped due to validation</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Failed Imports</p>
          <p className="metric-value">{historyStats.failed}</p>
          <p className="metric-meta">
            Partial: {historyStats.partial} · Errors: {historyStats.errors}
          </p>
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">Recommended Flow</p>
            <h2 className="section-title">Import Pipeline Order</h2>
            <p className="section-description">
              Upload data in this order so revenue and signals can be linked to
              existing customer accounts.
            </p>
          </div>

          {latestImport && (
            <span className={getStatusBadgeClass(latestImport.status)}>
              Last Import: {latestImport.status}
            </span>
          )}
        </div>

        <div className="grid-3">
          <div className="summary-box">
            <p className="summary-text">
              <strong>1. Customers</strong>
            </p>
            <p className="summary-note">
              Create CRM accounts first. Orders and signals use customer email,
              name, or handle to link activity.
            </p>
          </div>

          <div className="summary-box">
            <p className="summary-text">
              <strong>2. Orders</strong>
            </p>
            <p className="summary-note">
              Attach revenue history using <strong>customer_email</strong>.
              These records power sales metrics and account value.
            </p>
          </div>

          <div className="summary-box">
            <p className="summary-text">
              <strong>3. Customer Signals</strong>
            </p>
            <p className="summary-note">
              Import external interactions. AI analyzes sentiment, intent, risk,
              and can create execution actions.
            </p>
          </div>
        </div>
      </section>

      <section className="grid-3">
        {renderImportCard({
          step: 1,
          title: "Customers",
          subtitle:
            "Import customer accounts before orders and signals so activity can be linked correctly.",
          file: customersFile,
          setFile: setCustomersFile,
          result: customersResult,
          onUpload: () =>
            uploadStandardFile("customers", customersFile, setCustomersResult),
          loadingKey: "customers",
          accentBadge: "badge badge-blue",
        })}

        {renderImportCard({
          step: 2,
          title: "Orders",
          subtitle:
            "Import revenue activity linked to customers by customer_email.",
          file: ordersFile,
          setFile: setOrdersFile,
          result: ordersResult,
          onUpload: () =>
            uploadStandardFile("orders", ordersFile, setOrdersResult),
          loadingKey: "orders",
          accentBadge: "badge badge-green",
        })}

        {renderImportCard({
          step: 3,
          title: "Signals",
          subtitle:
            "Import customer interactions from web forms, support, email, social, or external systems.",
          file: signalsFile,
          setFile: setSignalsFile,
          result: signalsResult,
          onUpload: uploadSignalsFile,
          loadingKey: "signals",
          accentBadge: "badge badge-purple",
        })}
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">CSV Reference</p>
            <h2 className="section-title">Required File Formats</h2>
            <p className="section-description">
              Use these column names exactly so the import pipeline can parse
              and validate your files.
            </p>
          </div>
        </div>

        <div className="grid-3">
          {renderCsvRequirements(
            "customers.csv",
            ["name", "email", "phone", "company"],
            [
              {
                name: "Ahmad Saleh",
                email: "ahmad@example.com",
                phone: "+970599000000",
                company: "Nablus Retail Co",
              },
            ]
          )}

          {renderCsvRequirements(
            "orders.csv",
            ["customer_email", "product_name", "amount"],
            [
              {
                customer_email: "ahmad@example.com",
                product_name: "CRM Pro Plan",
                amount: "1200",
              },
            ]
          )}

          {renderCsvRequirements(
            "signals.csv",
            [
              "source",
              "author_name",
              "author_handle",
              "content",
              "external_post_url",
            ],
            [
              {
                source: "support_ticket",
                author_name: "Ahmad Saleh",
                author_handle: "ahmad@example.com",
                content: "The delivery was late and I need help.",
                external_post_url: "https://example.com/ticket/1001",
              },
            ]
          )}
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">Import History</p>
            <h2 className="section-title">Pipeline Activity</h2>
            <p className="section-description">
              Track previous import runs, inserted rows, skipped rows, and data
              quality issues.
            </p>
          </div>

          <button className="btn btn-secondary" onClick={fetchImportHistory}>
            Refresh
          </button>
        </div>

        {historyLoading ? (
          <div className="loading-state">Loading import history...</div>
        ) : history.length === 0 ? (
          <div className="empty-state">
            No imports yet. Start by uploading customers.csv.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Entity</th>
                  <th>File</th>
                  <th>Inserted</th>
                  <th>Skipped</th>
                  <th>Errors</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>

              <tbody>
                {history.map((log) => (
                  <tr key={log.id}>
                    <td>#{log.id}</td>

                    <td>
                      <span className={getEntityBadgeClass(log.entity_type)}>
                        {formatEntityLabel(log.entity_type)}
                      </span>
                    </td>

                    <td>{log.file_name}</td>

                    <td>{log.inserted_count}</td>

                    <td>{log.skipped_count}</td>

                    <td>{log.error_count}</td>

                    <td>
                      <span className={getStatusBadgeClass(log.status)}>
                        {log.status}
                      </span>
                    </td>

                    <td>{formatDate(log.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default DataImport;