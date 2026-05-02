import { useEffect, useMemo, useState } from "react";
import api from "../services/api";

function SocialListener() {
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [convertingId, setConvertingId] = useState(null);
  const [linkingId, setLinkingId] = useState(null);

  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [filters, setFilters] = useState({
    source: "",
    intent: "",
    risk_level: "",
    only_unmatched: false,
    search: "",
  });

  const [linkInputs, setLinkInputs] = useState({});

  const fetchSignals = async (isRefresh = false) => {
    try {
      setError("");
      setSuccessMessage("");

      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const params = {
        limit: 150,
      };

      if (filters.source) params.source = filters.source;
      if (filters.intent) params.intent = filters.intent;
      if (filters.risk_level) params.risk_level = filters.risk_level;
      if (filters.only_unmatched) params.only_unmatched = true;

      const response = await api.get("/social-listener/", { params });
      setSignals(response.data || []);
    } catch (error) {
      console.error("Error fetching customer signals:", error);
      setSignals([]);
      setError("Could not load customer signals. Make sure the backend is running.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSignals();
  }, [
    filters.source,
    filters.intent,
    filters.risk_level,
    filters.only_unmatched,
  ]);

  const clearFilters = () => {
    setFilters({
      source: "",
      intent: "",
      risk_level: "",
      only_unmatched: false,
      search: "",
    });
  };

  const handleFilterChange = (e) => {
    const { name, value, type, checked } = e.target;

    setFilters((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleLinkInputChange = (signalId, value) => {
    setLinkInputs((prev) => ({
      ...prev,
      [signalId]: value,
    }));
  };

  const convertToCustomer = async (signal) => {
    try {
      setConvertingId(signal.id);
      setError("");
      setSuccessMessage("");

      const payload = {
        name: signal.author_name || `Lead from Signal #${signal.id}`,
        email:
          signal.author_handle && signal.author_handle.includes("@")
            ? signal.author_handle
            : undefined,
        phone: "Unknown",
        company: "Unmatched Leads",
      };

      const response = await api.post(
        `/social-listener/${signal.id}/convert-to-customer`,
        payload
      );

      await fetchSignals(true);

      const customerName =
        response.data?.customer?.name ||
        payload.name ||
        `Signal #${signal.id}`;

      setSuccessMessage(
        `Signal #${signal.id} was converted into customer: ${customerName}.`
      );
    } catch (error) {
      console.error("Error converting signal to customer:", error);
      setError(
        error?.response?.data?.detail ||
          "Could not convert signal to customer."
      );
    } finally {
      setConvertingId(null);
    }
  };

  const linkToExistingCustomer = async (signalId) => {
    const customerId = linkInputs[signalId];

    if (!customerId) {
      setError("Please enter a customer ID before linking the signal.");
      return;
    }

    try {
      setLinkingId(signalId);
      setError("");
      setSuccessMessage("");

      await api.put(`/social-listener/${signalId}/link-customer/${customerId}`);
      await fetchSignals(true);

      setLinkInputs((prev) => ({
        ...prev,
        [signalId]: "",
      }));

      setSuccessMessage(
        `Signal #${signalId} was linked to customer #${customerId}.`
      );
    } catch (error) {
      console.error("Error linking signal to customer:", error);
      setError(
        error?.response?.data?.detail ||
          "Could not link signal to customer. Check the customer ID."
      );
    } finally {
      setLinkingId(null);
    }
  };

  const filteredSignals = useMemo(() => {
    const searchValue = filters.search.trim().toLowerCase();

    if (!searchValue) return signals;

    return signals.filter((signal) => {
      const searchableText = [
        signal.id,
        signal.customer_id ? `customer ${signal.customer_id}` : "unmatched",
        signal.source,
        signal.author_name,
        signal.author_handle,
        signal.content,
        signal.sentiment,
        signal.intent,
        signal.risk_level,
        signal.external_post_url,
      ]
        .join(" ")
        .toLowerCase();

      return searchableText.includes(searchValue);
    });
  }, [signals, filters.search]);

  const stats = useMemo(() => {
    const total = signals.length;

    const highRisk = signals.filter(
      (signal) => signal.risk_level === "high"
    ).length;

    const mediumRisk = signals.filter(
      (signal) => signal.risk_level === "medium"
    ).length;

    const lowRisk = signals.filter(
      (signal) => signal.risk_level === "low"
    ).length;

    const complaints = signals.filter(
      (signal) => signal.intent === "complaint"
    ).length;

    const inquiries = signals.filter(
      (signal) => signal.intent === "inquiry"
    ).length;

    const praise = signals.filter(
      (signal) => signal.intent === "praise"
    ).length;

    const unmatched = signals.filter((signal) => !signal.customer_id).length;
    const matched = total - unmatched;

    const matchRate = total > 0 ? Math.round((matched / total) * 100) : 0;

    return {
      total,
      highRisk,
      mediumRisk,
      lowRisk,
      complaints,
      inquiries,
      praise,
      unmatched,
      matched,
      matchRate,
    };
  }, [signals]);

  const recommendedFocus = useMemo(() => {
    const highRiskUnmatched = signals.find(
      (signal) => signal.risk_level === "high" && !signal.customer_id
    );

    if (highRiskUnmatched) {
      return {
        title: `High-risk unmatched signal #${highRiskUnmatched.id}`,
        message:
          "Start here. This signal is high risk and not linked to a customer yet.",
        badge: "Risk + Unmatched",
        badgeClass: "badge badge-red",
      };
    }

    const complaint = signals.find((signal) => signal.intent === "complaint");

    if (complaint) {
      return {
        title: `Complaint signal #${complaint.id}`,
        message:
          "Review complaint signals before growth opportunities to protect retention.",
        badge: "Complaint",
        badgeClass: "badge badge-red",
      };
    }

    const inquiry = signals.find((signal) => signal.intent === "inquiry");

    if (inquiry) {
      return {
        title: `Inquiry signal #${inquiry.id}`,
        message:
          "This may represent a sales opportunity. Link it to a customer or convert it into a lead.",
        badge: "Opportunity",
        badgeClass: "badge badge-blue",
      };
    }

    const unmatched = signals.find((signal) => !signal.customer_id);

    if (unmatched) {
      return {
        title: `Unmatched signal #${unmatched.id}`,
        message:
          "Clean up unmatched signals by linking them to existing customers or converting them into leads.",
        badge: "Lead Cleanup",
        badgeClass: "badge badge-yellow",
      };
    }

    return {
      title: "Signal inbox is clean",
      message:
        "No urgent unmatched or high-risk signal stands out in the current view.",
      badge: "Stable",
      badgeClass: "badge badge-green",
    };
  }, [signals]);

  const sourceDistribution = useMemo(() => {
    const map = {};

    signals.forEach((signal) => {
      const key = signal.source || "unknown";
      map[key] = (map[key] || 0) + 1;
    });

    return Object.entries(map)
      .map(([source, count]) => ({ source, count }))
      .sort((a, b) => b.count - a.count);
  }, [signals]);

  const intentDistribution = useMemo(() => {
    const map = {};

    signals.forEach((signal) => {
      const key = signal.intent || "unknown";
      map[key] = (map[key] || 0) + 1;
    });

    return Object.entries(map)
      .map(([intent, count]) => ({ intent, count }))
      .sort((a, b) => b.count - a.count);
  }, [signals]);

  const formatDate = (value) => {
    if (!value) return "-";
    return new Date(value).toLocaleString();
  };

  const getRiskBadgeClass = (risk) => {
    if (risk === "high") return "badge badge-red";
    if (risk === "medium") return "badge badge-yellow";
    return "badge badge-green";
  };

  const getIntentBadgeClass = (intent) => {
    if (intent === "complaint") return "badge badge-red";
    if (intent === "inquiry") return "badge badge-blue";
    if (intent === "praise") return "badge badge-green";
    return "badge badge-purple";
  };

  const getSentimentBadgeClass = (sentiment) => {
    if (sentiment === "negative") return "badge badge-red";
    if (sentiment === "positive") return "badge badge-green";
    return "badge badge-yellow";
  };

  const getSourceBadgeClass = (source) => {
    if (source === "support_ticket") return "badge badge-red";
    if (source === "website_form") return "badge badge-blue";
    if (source === "email") return "badge badge-purple";
    if (source === "manual_import") return "badge badge-yellow";
    return "badge badge-blue";
  };

  const getSourceLabel = (source) => {
    const labels = {
      facebook: "Facebook",
      instagram: "Instagram",
      website: "Website",
      website_form: "Website Form",
      support_ticket: "Support Ticket",
      email: "Email",
      api_webhook: "API Webhook",
      manual_import: "Manual Import",
    };

    return labels[source] || source || "Unknown";
  };

  const renderDistribution = (items, keyName, labelFormatter) => {
    if (!items || items.length === 0) {
      return <div className="empty-state">No data available.</div>;
    }

    const maxValue = Math.max(...items.map((item) => item.count || 0), 1);

    return (
      <div className="list">
        {items.slice(0, 6).map((item) => {
          const label = item[keyName] || "unknown";
          const width = `${Math.max(8, ((item.count || 0) / maxValue) * 100)}%`;

          return (
            <div key={label} className="summary-box">
              <div className="results-bar">
                <p className="summary-text">
                  <strong>
                    {labelFormatter ? labelFormatter(label) : label}
                  </strong>
                </p>

                <span className="badge badge-blue">{item.count}</span>
              </div>

              <div
                style={{
                  marginTop: 10,
                  width: "100%",
                  height: 10,
                  background: "#e2e8f0",
                  borderRadius: 999,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width,
                    height: "100%",
                    background: "#2563eb",
                    borderRadius: 999,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderSignalCard = (signal) => {
    const isUnmatched = !signal.customer_id;
    const isHighRisk = signal.risk_level === "high";
    const isComplaint = signal.intent === "complaint";
    const isInquiry = signal.intent === "inquiry";

    return (
      <div key={signal.id} className="list-row">
        <div>
          <div className="btn-row" style={{ marginBottom: 12 }}>
            <span className={getSourceBadgeClass(signal.source)}>
              {getSourceLabel(signal.source)}
            </span>

            <span className={getSentimentBadgeClass(signal.sentiment)}>
              {String(signal.sentiment || "neutral").toUpperCase()}
            </span>

            <span className={getIntentBadgeClass(signal.intent)}>
              {String(signal.intent || "other").toUpperCase()}
            </span>

            <span className={getRiskBadgeClass(signal.risk_level)}>
              {String(signal.risk_level || "low").toUpperCase()} RISK
            </span>

            {isUnmatched ? (
              <span className="badge badge-yellow">Unmatched Lead</span>
            ) : (
              <span className="badge badge-green">
                Customer #{signal.customer_id}
              </span>
            )}

            {isHighRisk && <span className="badge badge-red">Needs Review</span>}
            {isInquiry && <span className="badge badge-blue">Sales Signal</span>}
            {isComplaint && <span className="badge badge-red">Retention Signal</span>}
          </div>

          <p className="list-title">
            {signal.author_name || signal.author_handle || "Unknown author"}
          </p>

          <p className="list-meta">
            {signal.author_handle ? `Handle / Email: ${signal.author_handle}` : "No handle provided"} · Received:{" "}
            {formatDate(signal.created_at)}
          </p>

          <p className="list-description">{signal.content}</p>

          {signal.external_post_url && (
            <p className="summary-note">
              External URL: {signal.external_post_url}
            </p>
          )}

          {isUnmatched && (
            <div className="summary-box" style={{ marginTop: 14 }}>
              <p className="section-eyebrow">Lead Management</p>

              <p className="summary-text">
                This customer signal is not linked to a CRM customer yet.
              </p>

              <p className="summary-note">
                Convert it into a new customer, or link it to an existing customer
                by ID. Related AI actions will be linked automatically by the
                backend.
              </p>

              <div className="btn-row" style={{ marginTop: 12 }}>
                <button
                  className="btn btn-primary"
                  onClick={() => convertToCustomer(signal)}
                  disabled={convertingId === signal.id}
                >
                  {convertingId === signal.id
                    ? "Converting..."
                    : "Convert to Customer"}
                </button>
              </div>

              <div className="search-row" style={{ marginTop: 12 }}>
                <input
                  className="input"
                  type="number"
                  placeholder="Existing Customer ID"
                  value={linkInputs[signal.id] || ""}
                  onChange={(e) =>
                    handleLinkInputChange(signal.id, e.target.value)
                  }
                />

                <button
                  className="btn btn-secondary"
                  onClick={() => linkToExistingCustomer(signal.id)}
                  disabled={linkingId === signal.id}
                >
                  {linkingId === signal.id
                    ? "Linking..."
                    : "Link to Customer"}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="right-meta">
          <div className="kv-list">
            <div className="kv-row">
              <span className="kv-key">Signal ID</span>
              <span className="kv-value">#{signal.id}</span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Customer Link</span>
              <span className="kv-value">
                {signal.customer_id ? `Customer #${signal.customer_id}` : "Unmatched"}
              </span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Source</span>
              <span className="kv-value">{getSourceLabel(signal.source)}</span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Intent</span>
              <span className="kv-value">{signal.intent || "-"}</span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Risk</span>
              <span className="kv-value">{signal.risk_level || "-"}</span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Sentiment</span>
              <span className="kv-value">{signal.sentiment || "-"}</span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="page">
      <section className="page-hero">
        <div>
          <p className="page-eyebrow">Customer Intelligence</p>
          <h1 className="page-title">Social Listener</h1>
          <p className="page-subtitle">
            Monitor customer signals from website forms, support tickets, email,
            social sources, imports, and webhooks. Unmatched signals can become
            CRM leads or be linked to existing customers.
          </p>
        </div>

        <div className="hero-actions">
          <button
            className="btn btn-secondary"
            onClick={() => fetchSignals(true)}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing..." : "Refresh Signals"}
          </button>

          <button className="btn btn-primary" onClick={clearFilters}>
            Clear Filters
          </button>
        </div>
      </section>

      {error && <div className="error-state">{error}</div>}

      {successMessage && (
        <div className="summary-box">
          <p className="summary-text">
            <strong>Success:</strong> {successMessage}
          </p>
        </div>
      )}

      <section className="grid-4">
        <div className="metric-card">
          <p className="metric-label">Total Signals</p>
          <p className="metric-value">{stats.total}</p>
          <p className="metric-meta">Customer interactions in current view</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">High Risk</p>
          <p className="metric-value">{stats.highRisk}</p>
          <p className="metric-meta">Signals needing urgent review</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Inquiries</p>
          <p className="metric-value">{stats.inquiries}</p>
          <p className="metric-meta">Potential sales opportunities</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Unmatched Leads</p>
          <p className="metric-value">{stats.unmatched}</p>
          <p className="metric-meta">{stats.matchRate}% match rate</p>
        </div>
      </section>

      <section className="grid-4">
        <div className="metric-card">
          <p className="metric-label">Complaints</p>
          <p className="metric-value">{stats.complaints}</p>
          <p className="metric-meta">Retention-related customer signals</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Praise</p>
          <p className="metric-value">{stats.praise}</p>
          <p className="metric-meta">Positive feedback and growth signals</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Matched</p>
          <p className="metric-value">{stats.matched}</p>
          <p className="metric-meta">Signals linked to CRM customers</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Medium / Low Risk</p>
          <p className="metric-value">
            {stats.mediumRisk} / {stats.lowRisk}
          </p>
          <p className="metric-meta">Non-critical signal volume</p>
        </div>
      </section>

      <section className="grid-2">
        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Recommended Focus</p>
              <h2 className="section-title">{recommendedFocus.title}</h2>
              <p className="section-description">
                {recommendedFocus.message}
              </p>
            </div>

            <span className={recommendedFocus.badgeClass}>
              {recommendedFocus.badge}
            </span>
          </div>
        </div>

        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Signal Pipeline</p>
              <h2 className="section-title">Inbox Health</h2>
              <p className="section-description">
                The goal is to keep high-risk signals handled and unmatched
                signals linked or converted.
              </p>
            </div>
          </div>

          <div className="btn-row">
            <span className="badge badge-green">Matched {stats.matched}</span>
            <span className="badge badge-yellow">Unmatched {stats.unmatched}</span>
            <span className="badge badge-red">High Risk {stats.highRisk}</span>
            <span className="badge badge-blue">Match Rate {stats.matchRate}%</span>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">Filters</p>
            <h2 className="section-title">Filter Signal Inbox</h2>
            <p className="section-description">
              Narrow down by source, intent, risk level, unmatched status, or
              keyword search.
            </p>
          </div>

          <button className="btn btn-secondary" onClick={clearFilters}>
            Clear Filters
          </button>
        </div>

        <div className="filters-grid">
          <div className="search-row">
            <input
              className="input"
              type="text"
              name="search"
              placeholder="Search by author, content, signal ID, customer ID, source, intent, or risk..."
              value={filters.search}
              onChange={handleFilterChange}
            />

            <button
              className="btn btn-primary"
              onClick={() => fetchSignals(true)}
              disabled={refreshing}
            >
              Refresh
            </button>
          </div>

          <div className="filter-row">
            <select
              className="select"
              name="source"
              value={filters.source}
              onChange={handleFilterChange}
            >
              <option value="">All Sources</option>
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="website">Website</option>
              <option value="website_form">Website Form</option>
              <option value="support_ticket">Support Ticket</option>
              <option value="email">Email</option>
              <option value="api_webhook">API Webhook</option>
              <option value="manual_import">Manual Import</option>
            </select>

            <select
              className="select"
              name="intent"
              value={filters.intent}
              onChange={handleFilterChange}
            >
              <option value="">All Intents</option>
              <option value="complaint">Complaint</option>
              <option value="inquiry">Inquiry</option>
              <option value="praise">Praise</option>
              <option value="other">Other</option>
            </select>

            <select
              className="select"
              name="risk_level"
              value={filters.risk_level}
              onChange={handleFilterChange}
            >
              <option value="">All Risk Levels</option>
              <option value="high">High Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="low">Low Risk</option>
            </select>
          </div>

          <label className="summary-box" style={{ display: "block" }}>
            <input
              type="checkbox"
              name="only_unmatched"
              checked={filters.only_unmatched}
              onChange={handleFilterChange}
              style={{ marginRight: 8 }}
            />
            Show only unmatched signals / possible leads
          </label>
        </div>
      </section>

      <section className="grid-2">
        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Sources</p>
              <h2 className="section-title">Signals by Source</h2>
            </div>
          </div>

          {renderDistribution(sourceDistribution, "source", getSourceLabel)}
        </div>

        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Intent</p>
              <h2 className="section-title">Signals by Intent</h2>
            </div>
          </div>

          {renderDistribution(intentDistribution, "intent")}
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">Inbox</p>
            <h2 className="section-title">Incoming Customer Signals</h2>
            <p className="section-description">
              Review signals, identify leads, and connect customer activity to
              the CRM.
            </p>
          </div>

          <p className="results-text">
            Showing {filteredSignals.length} of {signals.length} signals
          </p>
        </div>

        {loading ? (
          <div className="loading-state">Loading customer signals...</div>
        ) : filteredSignals.length === 0 ? (
          <div className="empty-state">
            No signals match the current filters. Import signals or clear filters.
          </div>
        ) : (
          <div className="list">
            {filteredSignals.map((signal) => renderSignalCard(signal))}
          </div>
        )}
      </section>
    </div>
  );
}

export default SocialListener;