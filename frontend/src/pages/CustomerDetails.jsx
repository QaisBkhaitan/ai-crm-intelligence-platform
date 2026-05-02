import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../services/api";

function CustomerDetails() {
  const { id } = useParams();

  const [customer, setCustomer] = useState(null);
  const [customerLoading, setCustomerLoading] = useState(true);

  const [orders, setOrders] = useState([]);
  const [orderData, setOrderData] = useState({
    product_name: "",
    amount: "",
  });

  const [intelligence, setIntelligence] = useState(null);
  const [intelligenceLoading, setIntelligenceLoading] = useState(false);

  const [customerInsights, setCustomerInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);

  const [signalWorkspace, setSignalWorkspace] = useState(null);
  const [workspaceLoading, setWorkspaceLoading] = useState(false);

  const [updatingActionId, setUpdatingActionId] = useState(null);
  const [addingOrder, setAddingOrder] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadCustomer360();
  }, [id]);

  const loadCustomer360 = async () => {
    setError("");

    await Promise.all([
      fetchCustomer(),
      fetchOrders(),
      fetchCustomerIntelligence(),
      fetchCustomerInsights(),
      fetchSignalWorkspace(),
    ]);
  };

  const fetchCustomer = async () => {
    try {
      setCustomerLoading(true);
      const response = await api.get(`/customers/${id}`);
      setCustomer(response.data?.error ? null : response.data);
    } catch (error) {
      console.error("Error fetching customer:", error);
      setCustomer(null);
      setError("Could not load customer profile.");
    } finally {
      setCustomerLoading(false);
    }
  };

  const fetchOrders = async () => {
    try {
      const response = await api.get(`/orders/${id}`);
      setOrders(response.data || []);
    } catch (error) {
      console.error("Error fetching orders:", error);
      setOrders([]);
    }
  };

  const fetchCustomerIntelligence = async () => {
    try {
      setIntelligenceLoading(true);
      const response = await api.get(`/ai/customer-intelligence/${id}`);
      setIntelligence(response.data?.error ? null : response.data);
    } catch (error) {
      console.error("Error fetching customer intelligence:", error);
      setIntelligence(null);
    } finally {
      setIntelligenceLoading(false);
    }
  };

  const fetchCustomerInsights = async () => {
    try {
      setInsightsLoading(true);
      const response = await api.get(`/ai/customer-insights/${id}`);
      setCustomerInsights(response.data?.error ? null : response.data);
    } catch (error) {
      console.error("Error fetching customer AI insights:", error);
      setCustomerInsights(null);
    } finally {
      setInsightsLoading(false);
    }
  };

  const fetchSignalWorkspace = async () => {
    try {
      setWorkspaceLoading(true);
      const response = await api.get(`/social-listener/customer/${id}`);
      setSignalWorkspace(response.data || null);
    } catch (error) {
      console.error("Error fetching signal workspace:", error);
      setSignalWorkspace(null);
    } finally {
      setWorkspaceLoading(false);
    }
  };

  const refreshCustomer360 = async () => {
    await loadCustomer360();
  };

  const handleOrderChange = (e) => {
    setOrderData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleAddOrder = async (e) => {
    e.preventDefault();

    if (!orderData.product_name.trim() || !orderData.amount) {
      setError("Please enter product name and amount.");
      return;
    }

    try {
      setAddingOrder(true);
      setError("");

      await api.post(`/orders/${id}`, {
        product_name: orderData.product_name.trim(),
        amount: Number(orderData.amount),
      });

      setOrderData({
        product_name: "",
        amount: "",
      });

      await Promise.all([
        fetchOrders(),
        fetchCustomerIntelligence(),
        fetchCustomerInsights(),
        fetchSignalWorkspace(),
      ]);
    } catch (error) {
      console.error("Error adding order:", error);
      setError("Could not add order.");
    } finally {
      setAddingOrder(false);
    }
  };

  const completeAction = async (actionId) => {
    try {
      setUpdatingActionId(actionId);
      setError("");

      await api.put(`/actions/${actionId}/complete`);

      await Promise.all([
        fetchSignalWorkspace(),
        fetchCustomerIntelligence(),
        fetchCustomerInsights(),
      ]);
    } catch (error) {
      console.error("Error completing action:", error);
      setError("Could not complete action.");
    } finally {
      setUpdatingActionId(null);
    }
  };

  const cancelAction = async (actionId) => {
    try {
      setUpdatingActionId(actionId);
      setError("");

      await api.put(`/actions/${actionId}/cancel`);

      await Promise.all([
        fetchSignalWorkspace(),
        fetchCustomerIntelligence(),
        fetchCustomerInsights(),
      ]);
    } catch (error) {
      console.error("Error cancelling action:", error);
      setError("Could not cancel action.");
    } finally {
      setUpdatingActionId(null);
    }
  };

  const totalSales = useMemo(() => {
    return orders.reduce((sum, order) => sum + Number(order.amount || 0), 0);
  }, [orders]);

  const workspaceSummary = signalWorkspace?.summary || {
    total_signals: 0,
    high_risk_signals: 0,
    complaints: 0,
    inquiries: 0,
    praise: 0,
    total_actions: 0,
    pending_actions: 0,
    completed_actions: 0,
    high_priority_actions: 0,
    relationship_status: "quiet",
  };

  const insightSummary = customerInsights?.insight_summary || {};
  const aiRecommendation = customerInsights?.ai_recommendation || {};
  const contextPreview = customerInsights?.context_preview || {};

  const signals =
    customerInsights?.recent_signals ||
    signalWorkspace?.signals ||
    [];

  const actions =
    customerInsights?.recent_actions ||
    signalWorkspace?.actions ||
    [];

  const recentOrders =
    customerInsights?.recent_orders?.length > 0
      ? customerInsights.recent_orders
      : orders;

  const pendingActions = actions.filter((action) => action.status === "pending");
  const highRiskSignals = signals.filter((signal) => signal.risk_level === "high");

  const effectiveTotalSales =
    intelligence?.total_sales ??
    insightSummary.total_sales ??
    totalSales;

  const effectiveTotalOrders =
    intelligence?.total_orders ??
    insightSummary.total_orders ??
    orders.length;

  const effectiveTotalSignals =
    intelligence?.total_signals ??
    insightSummary.total_signals ??
    workspaceSummary.total_signals ??
    signals.length;

  const effectivePendingActions =
    intelligence?.pending_actions ??
    insightSummary.pending_actions ??
    workspaceSummary.pending_actions ??
    pendingActions.length;

  const effectiveHighRiskSignals =
    intelligence?.high_risk_signals ??
    insightSummary.high_risk_signals ??
    workspaceSummary.high_risk_signals ??
    highRiskSignals.length;

  const effectiveHealthScore =
    intelligence?.health_score ??
    insightSummary.health_score ??
    0;

  const effectiveStatus =
    intelligence?.status ??
    insightSummary.status ??
    "cold";

  const effectiveRelationshipStatus =
    intelligence?.relationship_status ??
    insightSummary.relationship_status ??
    workspaceSummary.relationship_status ??
    "quiet";

  const effectiveRiskLevel =
    intelligence?.risk_level ??
    insightSummary.risk_level ??
    (effectiveHighRiskSignals > 0 ? "high" : "low");

  const nextBestAction =
    aiRecommendation.next_best_action ||
    intelligence?.next_best_action ||
    intelligence?.recommended_action ||
    "Open recent signals, orders, and actions to decide the next best step.";

  const accountSummary =
    aiRecommendation.account_summary ||
    `${customer?.name || "This customer"} has ${effectiveTotalOrders} order(s), ${effectiveTotalSignals} linked signal(s), and ${effectivePendingActions} pending action(s).`;

  const riskAssessment =
    aiRecommendation.risk_assessment ||
    intelligence?.risk_reason ||
    "No detailed risk assessment available yet.";

  const opportunityAssessment =
    aiRecommendation.opportunity_assessment ||
    intelligence?.opportunity_reason ||
    "No detailed opportunity assessment available yet.";

  const suggestedFollowUp =
    aiRecommendation.suggested_follow_up_message ||
    "No suggested follow-up message available yet.";

  const formatDate = (value) => {
    if (!value) return "-";
    return new Date(value).toLocaleString();
  };

  const formatCurrency = (value) => `$${Number(value || 0).toLocaleString()}`;

  const getHealthBadgeClass = (status) => {
    if (status === "hot") return "badge badge-green";
    if (status === "warm") return "badge badge-yellow";
    return "badge badge-red";
  };

  const getRelationshipBadgeClass = (status) => {
    if (status === "needs_attention") return "badge badge-red";
    if (status === "active_opportunity") return "badge badge-blue";
    if (status === "engaged") return "badge badge-green";
    return "badge badge-yellow";
  };

  const getRelationshipLabel = (status) => {
    const labels = {
      needs_attention: "Needs Attention",
      active_opportunity: "Active Opportunity",
      engaged: "Engaged",
      quiet: "Quiet",
    };

    return labels[status] || status || "Unknown";
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

  const getPriorityBadgeClass = (priority) => {
    if (priority === "high") return "badge badge-red";
    if (priority === "medium") return "badge badge-yellow";
    return "badge badge-blue";
  };

  const getStatusBadgeClass = (status) => {
    if (status === "completed") return "badge badge-green";
    if (status === "cancelled") return "badge badge-red";
    return "badge badge-yellow";
  };

  const getTypeBadgeClass = (type) => {
    if (type === "retention") return "badge badge-red";
    if (type === "upsell") return "badge badge-green";
    if (type === "follow_up") return "badge badge-blue";
    if (type === "review") return "badge badge-purple";
    return "badge badge-purple";
  };

  const formatActionType = (type) => {
    const labels = {
      follow_up: "Follow Up",
      retention: "Retention",
      upsell: "Upsell",
      review: "Review",
      data_cleanup: "Data Cleanup",
    };

    return labels[type] || type || "Action";
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
      csv_import: "CSV Import",
      manual: "Manual",
      ai: "AI",
    };

    return labels[source] || source || "Unknown";
  };

  if (customerLoading) {
    return <div className="loading-state">Loading customer 360...</div>;
  }

  if (!customer) {
    return <div className="empty-state">Customer not found.</div>;
  }

  return (
    <div className="page">
      <section className="card profile-card">
        <div>
          <p className="page-eyebrow">Customer 360 Workspace</p>

          <div className="profile-header-row">
            <h1 className="page-title" style={{ fontSize: "34px" }}>
              {customer.name}
            </h1>

            <span className={getHealthBadgeClass(effectiveStatus)}>
              {effectiveStatus.toUpperCase()}
            </span>

            <span className={getRelationshipBadgeClass(effectiveRelationshipStatus)}>
              {getRelationshipLabel(effectiveRelationshipStatus)}
            </span>

            <span className={getRiskBadgeClass(effectiveRiskLevel)}>
              {effectiveRiskLevel.toUpperCase()} RISK
            </span>
          </div>

          <p className="page-subtitle" style={{ marginTop: 8 }}>
            {customer.company}
          </p>

          <p className="summary-note" style={{ marginTop: 10 }}>
            {accountSummary}
          </p>
        </div>

        <div className="profile-contact-grid">
          <div className="info-box">
            <p className="info-label">Email</p>
            <p className="info-value">{customer.email}</p>
          </div>

          <div className="info-box">
            <p className="info-label">Phone</p>
            <p className="info-value">{customer.phone}</p>
          </div>

          <div className="info-box">
            <p className="info-label">Source</p>
            <p className="info-value">{getSourceLabel(customer.source)}</p>
          </div>

          <div className="info-box">
            <p className="info-label">Created</p>
            <p className="info-value">{formatDate(customer.created_at)}</p>
          </div>
        </div>
      </section>

      {error && <div className="error-state">{error}</div>}

      <section className="grid-4">
        <div className="metric-card">
          <p className="metric-label">Total Sales</p>
          <p className="metric-value">{formatCurrency(effectiveTotalSales)}</p>
          <p className="metric-meta">Revenue from this customer</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Orders</p>
          <p className="metric-value">{effectiveTotalOrders}</p>
          <p className="metric-meta">Commercial activity records</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Signals</p>
          <p className="metric-value">{effectiveTotalSignals}</p>
          <p className="metric-meta">Linked customer interactions</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Pending Actions</p>
          <p className="metric-value">{effectivePendingActions}</p>
          <p className="metric-meta">Open execution items</p>
        </div>
      </section>

      <section className="grid-4">
        <div className="metric-card">
          <p className="metric-label">Health Score</p>
          <p className="metric-value">{effectiveHealthScore}/100</p>
          <p className="metric-meta">AI account health estimate</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">High Risk Signals</p>
          <p className="metric-value">{effectiveHighRiskSignals}</p>
          <p className="metric-meta">Signals requiring attention</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Complaints</p>
          <p className="metric-value">
            {intelligence?.complaints ?? insightSummary.complaints ?? workspaceSummary.complaints ?? 0}
          </p>
          <p className="metric-meta">Negative customer intent</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Inquiries</p>
          <p className="metric-value">
            {intelligence?.inquiries ?? insightSummary.inquiries ?? workspaceSummary.inquiries ?? 0}
          </p>
          <p className="metric-meta">Potential sales opportunities</p>
        </div>
      </section>

      <section className="grid-2">
        <div className="stack">
          <section className="card">
            <div className="section-head">
              <div>
                <p className="section-eyebrow">AI Account Intelligence</p>
                <h2 className="section-title">Recommended Direction</h2>
                <p className="section-description">
                  AI-generated account summary based on orders, customer
                  signals, and execution actions.
                </p>
              </div>

              <button className="btn btn-secondary" onClick={refreshCustomer360}>
                Refresh
              </button>
            </div>

            {(intelligenceLoading || insightsLoading) ? (
              <div className="loading-state">Loading AI intelligence...</div>
            ) : (
              <div className="stack">
                <div className="summary-box">
                  <p className="section-eyebrow">Account Summary</p>
                  <p className="summary-text">{accountSummary}</p>
                </div>

                <div className="summary-box">
                  <p className="section-eyebrow">Next Best Action</p>
                  <p className="summary-text">
                    <strong>{nextBestAction}</strong>
                  </p>
                </div>

                <div className="summary-box">
                  <p className="section-eyebrow">Suggested Follow-up Message</p>
                  <p className="summary-text">{suggestedFollowUp}</p>
                </div>
              </div>
            )}
          </section>

          <section className="card">
            <div className="section-head">
              <div>
                <p className="section-eyebrow">Risk & Opportunity</p>
                <h2 className="section-title">Account Assessment</h2>
              </div>
            </div>

            <div className="grid-2">
              <div className="summary-box">
                <p className="section-eyebrow">Risk Assessment</p>
                <p className="summary-text">{riskAssessment}</p>
              </div>

              <div className="summary-box">
                <p className="section-eyebrow">Opportunity Assessment</p>
                <p className="summary-text">{opportunityAssessment}</p>
              </div>
            </div>
          </section>

          <section className="card">
            <div className="section-head">
              <div>
                <p className="section-eyebrow">Revenue History</p>
                <h2 className="section-title">Recent Orders</h2>
              </div>
            </div>

            <form onSubmit={handleAddOrder} className="form-grid">
              <div className="filter-row">
                <input
                  className="input"
                  type="text"
                  name="product_name"
                  placeholder="Product name"
                  value={orderData.product_name}
                  onChange={handleOrderChange}
                  required
                />

                <input
                  className="input"
                  type="number"
                  name="amount"
                  placeholder="Amount"
                  value={orderData.amount}
                  onChange={handleOrderChange}
                  min="0"
                  required
                />

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={addingOrder}
                >
                  {addingOrder ? "Adding..." : "Add Order"}
                </button>
              </div>
            </form>

            <div style={{ marginTop: 18 }}>
              {recentOrders.length === 0 ? (
                <div className="empty-state">No orders yet.</div>
              ) : (
                <div className="list">
                  {recentOrders.slice(0, 6).map((order) => (
                    <div key={order.id} className="list-row">
                      <div>
                        <p className="list-title">{order.product_name}</p>
                        <p className="list-meta">
                          Source: {getSourceLabel(order.source)} ·{" "}
                          {formatDate(order.created_at)}
                        </p>
                      </div>

                      <div className="right-meta">
                        <span className="badge badge-green">
                          {formatCurrency(order.amount)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="stack">
          <section className="card">
            <div className="section-head">
              <div>
                <p className="section-eyebrow">Execution Queue</p>
                <h2 className="section-title">Recent AI Actions</h2>
                <p className="section-description">
                  Complete or cancel pending work directly from the customer
                  workspace.
                </p>
              </div>
            </div>

            {workspaceLoading ? (
              <div className="loading-state">Loading actions...</div>
            ) : actions.length === 0 ? (
              <div className="empty-state">No actions linked to this customer.</div>
            ) : (
              <div className="list">
                {actions.slice(0, 7).map((action) => (
                  <div key={action.id} className="list-row-compact">
                    <div className="results-bar">
                      <div className="btn-row">
                        <span className={getTypeBadgeClass(action.action_type)}>
                          {formatActionType(action.action_type)}
                        </span>

                        <span className={getPriorityBadgeClass(action.priority)}>
                          {String(action.priority || "medium").toUpperCase()}
                        </span>

                        <span className={getStatusBadgeClass(action.status)}>
                          {String(action.status || "pending").toUpperCase()}
                        </span>
                      </div>

                      <p className="list-meta">{formatDate(action.created_at)}</p>
                    </div>

                    <p className="list-title" style={{ marginTop: 10 }}>
                      {action.title}
                    </p>

                    <p className="list-description">
                      {action.description}
                    </p>

                    {action.reason && (
                      <p className="summary-note">
                        <strong>AI Reason:</strong> {action.reason}
                      </p>
                    )}

                    {action.suggested_reply && (
                      <div className="summary-box" style={{ marginTop: 10 }}>
                        <p className="section-eyebrow">Suggested Reply</p>
                        <p className="summary-text">{action.suggested_reply}</p>
                      </div>
                    )}

                    {action.status === "pending" && (
                      <div className="btn-row" style={{ marginTop: 12 }}>
                        <button
                          className="btn btn-primary"
                          onClick={() => completeAction(action.id)}
                          disabled={updatingActionId === action.id}
                        >
                          {updatingActionId === action.id
                            ? "Updating..."
                            : "Complete"}
                        </button>

                        <button
                          className="btn btn-danger"
                          onClick={() => cancelAction(action.id)}
                          disabled={updatingActionId === action.id}
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card">
            <div className="section-head">
              <div>
                <p className="section-eyebrow">Customer Signals</p>
                <h2 className="section-title">Recent Signals</h2>
                <p className="section-description">
                  External interactions linked to this customer.
                </p>
              </div>
            </div>

            {workspaceLoading ? (
              <div className="loading-state">Loading signals...</div>
            ) : signals.length === 0 ? (
              <div className="empty-state">No linked customer signals yet.</div>
            ) : (
              <div className="list">
                {signals.slice(0, 7).map((signal) => (
                  <div key={signal.id} className="list-row-compact">
                    <div className="results-bar">
                      <div className="btn-row">
                        <span className="badge badge-blue">
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
                      </div>

                      <p className="list-meta">{formatDate(signal.created_at)}</p>
                    </div>

                    <p className="list-title" style={{ marginTop: 10 }}>
                      {signal.author_name || signal.author_handle || "Unknown author"}
                    </p>

                    <p className="list-description">{signal.content}</p>

                    {signal.external_post_url && (
                      <p className="summary-note">
                        External URL: {signal.external_post_url}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card">
            <div className="section-head">
              <div>
                <p className="section-eyebrow">Context Preview</p>
                <h2 className="section-title">Latest Activity</h2>
              </div>
            </div>

            <div className="kv-list">
              <div className="kv-row">
                <span className="kv-key">Latest Order</span>
                <span className="kv-value">
                  {contextPreview.latest_order || "No recent order."}
                </span>
              </div>

              <div className="kv-row">
                <span className="kv-key">Latest Signal</span>
                <span className="kv-value">
                  {contextPreview.latest_signal || "No recent signal."}
                </span>
              </div>

              <div className="kv-row">
                <span className="kv-key">Latest Action</span>
                <span className="kv-value">
                  {contextPreview.latest_action || "No recent action."}
                </span>
              </div>
            </div>
          </section>
        </div>
      </section>
    </div>
  );
}

export default CustomerDetails;