import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

function Customers() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");

  const [searchInput, setSearchInput] = useState("");

  const [filters, setFilters] = useState({
    search: "",
    company: "",
    source: "",
    created_after: "",
    created_before: "",
    sort_by: "id",
    sort_order: "desc",
    page: 1,
    limit: 6,
  });

  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    limit: 6,
    total_pages: 1,
  });

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    company: "",
  });

  const navigate = useNavigate();

  useEffect(() => {
    fetchCustomers();
  }, [filters]);

  const fetchCustomers = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get("/customers/query", { params: filters });

      setCustomers(response.data.items || []);
      setPagination(
        response.data.pagination || {
          total: 0,
          page: 1,
          limit: 6,
          total_pages: 1,
        }
      );
    } catch (error) {
      console.error("Error fetching customers:", error);
      setCustomers([]);
      setError("Could not load customers. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const handleFormChange = (e) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleAddCustomer = async (e) => {
    e.preventDefault();

    if (
      !formData.name.trim() ||
      !formData.email.trim() ||
      !formData.phone.trim() ||
      !formData.company.trim()
    ) {
      setError("Please fill all customer fields.");
      return;
    }

    try {
      setCreating(true);
      setError("");

      const response = await api.post("/customers", formData);

      if (response.data?.error) {
        setError(response.data.error);
        return;
      }

      setFormData({
        name: "",
        email: "",
        phone: "",
        company: "",
      });

      await fetchCustomers();
    } catch (error) {
      console.error("Error adding customer:", error);
      setError(error?.response?.data?.detail || "Could not add customer.");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteCustomer = async (id) => {
    const confirmed = window.confirm(
      "Delete this customer? This should only be used for demo cleanup."
    );

    if (!confirmed) return;

    try {
      setDeletingId(id);
      setError("");

      await api.delete(`/customers/${id}`);

      const shouldGoPrevPage = customers.length === 1 && pagination.page > 1;

      setFilters((prev) => ({
        ...prev,
        page: shouldGoPrevPage ? prev.page - 1 : prev.page,
      }));
    } catch (error) {
      console.error("Error deleting customer:", error);
      setError("Could not delete customer.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleSearch = () => {
    setFilters((prev) => ({
      ...prev,
      search: searchInput,
      page: 1,
    }));
  };

  const handleSearchKeyDown = (e) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;

    setFilters((prev) => ({
      ...prev,
      [name]: name === "limit" ? Number(value) : value,
      page: 1,
    }));
  };

  const clearFilters = () => {
    setSearchInput("");
    setFilters({
      search: "",
      company: "",
      source: "",
      created_after: "",
      created_before: "",
      sort_by: "id",
      sort_order: "desc",
      page: 1,
      limit: 6,
    });
  };

  const goToNextPage = () => {
    if (pagination.page < pagination.total_pages) {
      setFilters((prev) => ({
        ...prev,
        page: prev.page + 1,
      }));
    }
  };

  const goToPrevPage = () => {
    if (pagination.page > 1) {
      setFilters((prev) => ({
        ...prev,
        page: prev.page - 1,
      }));
    }
  };

  const formatDate = (value) => {
    if (!value) return "-";
    return new Date(value).toLocaleString();
  };

  const formatCurrency = (value) => `$${Number(value || 0).toLocaleString()}`;

  const getSourceLabel = (source) => {
    const labels = {
      manual: "Manual",
      csv_import: "CSV Import",
      website_form: "Website Form",
      api_webhook: "API Webhook",
    };

    return labels[source] || source || "Unknown";
  };

  const sourceBadgeClass = (source) =>
    source === "csv_import" ? "badge badge-purple" : "badge badge-blue";

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

  const dashboardStats = useMemo(() => {
    const totalVisible = customers.length;

    const visibleSales = customers.reduce((sum, customer) => {
      return sum + Number(customer.intelligence?.total_sales || 0);
    }, 0);

    const visiblePendingActions = customers.reduce((sum, customer) => {
      return sum + Number(customer.intelligence?.pending_actions || 0);
    }, 0);

    const visibleRiskAccounts = customers.filter((customer) => {
      return (
        customer.intelligence?.relationship_status === "needs_attention" ||
        customer.intelligence?.high_risk_signals > 0 ||
        customer.intelligence?.high_priority_actions > 0
      );
    }).length;

    return {
      totalVisible,
      visibleSales,
      visiblePendingActions,
      visibleRiskAccounts,
    };
  }, [customers]);

  return (
    <div className="page">
      <section className="page-hero">
        <div>
          <p className="page-eyebrow">CRM Workspace</p>
          <h1 className="page-title">Account Intelligence</h1>
          <p className="page-subtitle">
            Manage customer accounts with revenue context, signal activity,
            pending AI actions, relationship status, and next-best-action
            guidance from one CRM workspace.
          </p>
        </div>

        <div className="hero-actions">
          <button className="btn btn-secondary" onClick={fetchCustomers}>
            Refresh
          </button>
          <button
            className="btn btn-primary"
            onClick={() => navigate("/data-import")}
          >
            Import Data
          </button>
        </div>
      </section>

      {error && <div className="error-state">{error}</div>}

      <section className="grid-4">
        <div className="metric-card">
          <p className="metric-label">Visible Accounts</p>
          <p className="metric-value">{dashboardStats.totalVisible}</p>
          <p className="metric-meta">
            Showing {customers.length} of {pagination.total} total customers
          </p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Visible Revenue</p>
          <p className="metric-value">
            {formatCurrency(dashboardStats.visibleSales)}
          </p>
          <p className="metric-meta">Revenue from accounts on this page</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Pending Actions</p>
          <p className="metric-value">
            {dashboardStats.visiblePendingActions}
          </p>
          <p className="metric-meta">Open work across visible accounts</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Risk Accounts</p>
          <p className="metric-value">
            {dashboardStats.visibleRiskAccounts}
          </p>
          <p className="metric-meta">Accounts that need attention</p>
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">Manual Entry</p>
            <h2 className="section-title">Add Customer</h2>
            <p className="section-description">
              Add a single customer manually. For realistic demos, use the data
              import pipeline for larger datasets.
            </p>
          </div>
        </div>

        <form onSubmit={handleAddCustomer} className="form-grid">
          <div className="filter-row">
            <input
              className="input"
              type="text"
              name="name"
              placeholder="Name"
              value={formData.name}
              onChange={handleFormChange}
              required
            />

            <input
              className="input"
              type="email"
              name="email"
              placeholder="Email"
              value={formData.email}
              onChange={handleFormChange}
              required
            />

            <input
              className="input"
              type="text"
              name="phone"
              placeholder="Phone"
              value={formData.phone}
              onChange={handleFormChange}
              required
            />
          </div>

          <div className="filter-row">
            <input
              className="input"
              type="text"
              name="company"
              placeholder="Company"
              value={formData.company}
              onChange={handleFormChange}
              required
            />

            <div></div>
            <div></div>
          </div>

          <div className="btn-row">
            <button type="submit" className="btn btn-primary" disabled={creating}>
              {creating ? "Adding..." : "Add Customer"}
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">Query Layer</p>
            <h2 className="section-title">Advanced Account Query</h2>
            <p className="section-description">
              Search, filter, sort, and paginate customers while keeping their
              account intelligence visible.
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
              placeholder="Search by name, email, company, or phone."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={handleSearchKeyDown}
            />

            <button className="btn btn-primary" onClick={handleSearch}>
              Search
            </button>
          </div>

          <div className="filter-row">
            <input
              className="input"
              type="text"
              name="company"
              placeholder="Filter by company."
              value={filters.company}
              onChange={handleFilterChange}
            />

            <select
              className="select"
              name="source"
              value={filters.source}
              onChange={handleFilterChange}
            >
              <option value="">All Sources</option>
              <option value="manual">Manual</option>
              <option value="csv_import">CSV Import</option>
            </select>

            <select
              className="select"
              name="limit"
              value={filters.limit}
              onChange={handleFilterChange}
            >
              <option value={6}>6 per page</option>
              <option value={10}>10 per page</option>
              <option value={20}>20 per page</option>
            </select>
          </div>

          <div className="filter-row">
            <div className="date-field">
              <label className="label">Created After</label>
              <input
                className="input"
                type="date"
                name="created_after"
                value={filters.created_after}
                onChange={handleFilterChange}
              />
            </div>

            <div className="date-field">
              <label className="label">Created Before</label>
              <input
                className="input"
                type="date"
                name="created_before"
                value={filters.created_before}
                onChange={handleFilterChange}
              />
            </div>

            <div className="date-field">
              <label className="label">Sort</label>
              <div
                className="filter-row"
                style={{ gridTemplateColumns: "1fr 1fr" }}
              >
                <select
                  className="select"
                  name="sort_by"
                  value={filters.sort_by}
                  onChange={handleFilterChange}
                >
                  <option value="id">Sort by ID</option>
                  <option value="name">Sort by Name</option>
                  <option value="email">Sort by Email</option>
                  <option value="company">Sort by Company</option>
                  <option value="created_at">Sort by Created Date</option>
                  <option value="updated_at">Sort by Updated Date</option>
                </select>

                <select
                  className="select"
                  name="sort_order"
                  value={filters.sort_order}
                  onChange={handleFilterChange}
                >
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="results-bar">
          <p className="results-text">
            Showing <strong>{customers.length}</strong> accounts out of{" "}
            <strong>{pagination.total}</strong>
          </p>

          <p className="results-text">
            Page <strong>{pagination.page}</strong> of{" "}
            <strong>{pagination.total_pages}</strong>
          </p>
        </div>
      </section>

      {loading ? (
        <div className="loading-state">Loading account intelligence...</div>
      ) : customers.length === 0 ? (
        <div className="empty-state">No customers found.</div>
      ) : (
        <section className="customer-grid">
          {customers.map((customer) => {
            const intelligence = customer.intelligence || {};

            return (
              <div key={customer.id} className="customer-card">
                <div>
                  <div className="customer-top">
                    <div>
                      <h3 className="customer-name">{customer.name}</h3>
                      <p className="customer-company">{customer.company}</p>
                    </div>

                    <span className={sourceBadgeClass(customer.source)}>
                      {getSourceLabel(customer.source)}
                    </span>
                  </div>

                  <div className="btn-row" style={{ marginTop: 12 }}>
                    <span className={getHealthBadgeClass(intelligence.health_status)}>
                      {(intelligence.health_status || "unknown").toUpperCase()}
                    </span>

                    <span
                      className={getRelationshipBadgeClass(
                        intelligence.relationship_status
                      )}
                    >
                      {getRelationshipLabel(intelligence.relationship_status)}
                    </span>

                    <span className="badge badge-purple">
                      {intelligence.priority_label || "Account"}
                    </span>
                  </div>

                  <p className="customer-info" style={{ marginTop: 14 }}>
                    📧 {customer.email}
                  </p>
                  <p className="customer-info">📞 {customer.phone}</p>

                  <div className="grid-4" style={{ marginTop: 16 }}>
                    <div className="stat-box">
                      <p className="stat-label">Sales</p>
                      <p className="stat-value">
                        {formatCurrency(intelligence.total_sales)}
                      </p>
                    </div>

                    <div className="stat-box">
                      <p className="stat-label">Orders</p>
                      <p className="stat-value">
                        {intelligence.total_orders || 0}
                      </p>
                    </div>

                    <div className="stat-box">
                      <p className="stat-label">Signals</p>
                      <p className="stat-value">
                        {intelligence.total_signals || 0}
                      </p>
                    </div>

                    <div className="stat-box">
                      <p className="stat-label">Pending</p>
                      <p className="stat-value">
                        {intelligence.pending_actions || 0}
                      </p>
                    </div>
                  </div>

                  <div className="summary-box" style={{ marginTop: 16 }}>
                    <p className="summary-text">
                      <strong>Next best action:</strong>{" "}
                      {intelligence.next_best_action ||
                        "Open the customer workspace for more context."}
                    </p>

                    <p className="summary-note">
                      Health score:{" "}
                      <strong>{intelligence.health_score ?? 0}/100</strong>
                    </p>

                    <p className="summary-note">
                      High-risk signals:{" "}
                      <strong>{intelligence.high_risk_signals || 0}</strong> ·
                      High-priority actions:{" "}
                      <strong>{intelligence.high_priority_actions || 0}</strong>
                    </p>

                    <p className="summary-note">
                      Last activity:{" "}
                      <strong>
                        {formatDate(intelligence.last_activity_at)}
                      </strong>
                    </p>
                  </div>

                  <p className="customer-meta" style={{ marginTop: 12 }}>
                    Created: {formatDate(customer.created_at)}
                  </p>
                  <p className="customer-meta">
                    Updated: {formatDate(customer.updated_at)}
                  </p>
                </div>

                <div className="btn-row">
                  <button
                    className="btn btn-primary"
                    onClick={() => navigate(`/customers/${customer.id}`)}
                  >
                    Open Customer 360
                  </button>

                  <button
                    className="btn btn-secondary"
                    onClick={() => navigate("/actions")}
                  >
                    View Actions
                  </button>

                  <button
                    className="btn btn-danger"
                    onClick={() => handleDeleteCustomer(customer.id)}
                    disabled={deletingId === customer.id}
                  >
                    {deletingId === customer.id ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </div>
            );
          })}
        </section>
      )}

      <section className="pagination-bar">
        <button
          className="btn btn-secondary"
          onClick={goToPrevPage}
          disabled={pagination.page === 1}
        >
          Previous
        </button>

        <span className="page-info">
          Page {pagination.page} of {pagination.total_pages}
        </span>

        <button
          className="btn btn-secondary"
          onClick={goToNextPage}
          disabled={pagination.page === pagination.total_pages}
        >
          Next
        </button>
      </section>
    </div>
  );
}

export default Customers;