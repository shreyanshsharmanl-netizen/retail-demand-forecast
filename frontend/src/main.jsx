import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { buildChart } from "./chart";
import "./style.css";

const json = async (url, options) => {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
};

function Chart({ days }) {
  const c = buildChart(days, 620, 240);
  return (
    <svg viewBox="0 0 620 240" role="img" aria-label="Seven-day forecast compared with actual demand">
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1="34" x2="586" y1={c.y(c.top * f)} y2={c.y(c.top * f)} className="grid" />
          <text x="28" y={c.y(c.top * f) + 4} textAnchor="end">{Math.round(c.top * f)}</text>
        </g>
      ))}
      {days.map((d, i) => (
        <text key={d.date} x={c.x(i)} y="232" textAnchor="middle">{d.date.slice(5)}</text>
      ))}
      <path d={c.upper} className="upper" />
      <path d={c.forecast} className="forecast" />
      <path d={c.actual} className="actual" />
    </svg>
  );
}

function App() {
  const [data, setData] = useState(null);
  const [store, setStore] = useState("");
  const [risk, setRisk] = useState("");
  const [selected, setSelected] = useState(null);
  const [days, setDays] = useState([]);
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const query = new URLSearchParams();
    if (store) query.set("store_id", store);
    if (risk) query.set("risk", risk);
    json(`/api/recommendations?${query}`)
      .then((result) => {
        setData(result);
        setSelected((current) => current ?? result.rows[0] ?? null);
      })
      .catch((e) => setError(e.message));
  }, [store, risk]);

  useEffect(() => {
    json("/api/orders").then(setOrders).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    json(`/api/forecast/${selected.store_id}/${selected.item_id}`)
      .then(setDays)
      .catch((e) => setError(e.message));
  }, [selected]);

  async function placeOrder(row) {
    setError("");
    try {
      const order = await json("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ store_id: row.store_id, item_id: row.item_id, quantity: row.order_quantity }),
      });
      setOrders((current) => [order, ...current]);
    } catch (e) {
      setError(e.message);
    }
  }

  if (!data) return <main><p role="status">{error || "Loading forecasts..."}</p></main>;
  const high = data.rows.filter((r) => r.risk === "high").length;
  const units = data.rows.reduce((sum, r) => sum + r.order_quantity, 0);

  return (
    <main>
      <header>
        <div><h1>RetailCast</h1><p>Seven-day demand plan as of {data.as_of}. Store data is simulated.</p></div>
        <div className="filters">
          <label>Store<select value={store} onChange={(e) => setStore(e.target.value)}>
            <option value="">All</option><option>1</option><option>2</option><option>3</option>
          </select></label>
          <label>Risk<select value={risk} onChange={(e) => setRisk(e.target.value)}>
            <option value="">All</option><option value="high">High</option>
            <option value="medium">Medium</option><option value="low">Low</option>
          </select></label>
        </div>
      </header>
      {error && <p className="error" role="alert">{error}</p>}
      <section className="tiles">
        <div><span>Items shown</span><b>{data.rows.length}</b></div>
        <div><span>High stockout risk</span><b>{high}</b></div>
        <div><span>Units to order</span><b>{units.toLocaleString()}</b></div>
        <div><span>Orders placed</span><b>{orders.length}</b></div>
      </section>
      <section className="layout">
        <div className="table">
          <table>
            <thead><tr><th>Item</th><th>Store</th><th>Risk</th><th>Stock</th><th>7-day forecast</th><th>Order</th><th /></tr></thead>
            <tbody>
              {data.rows.slice(0, 40).map((row) => (
                <tr key={`${row.store_id}/${row.item_id}`}
                  className={selected?.item_id === row.item_id && selected?.store_id === row.store_id ? "active" : ""}
                  onClick={() => setSelected(row)}>
                  <td>{row.item_id}</td><td>{row.store_id}</td>
                  <td><span className={`risk ${row.risk}`}>{row.risk}</span></td>
                  <td>{row.stock}</td><td>{row.forecast_7d}</td><td>{row.order_quantity}</td>
                  <td><button disabled={!row.order_quantity}
                    onClick={(e) => { e.stopPropagation(); placeOrder(row); }}>Order</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <aside>
          <h2>{selected ? `${selected.item_id}, store ${selected.store_id}` : "Pick an item"}</h2>
          {days.length > 0 && <Chart days={days} />}
          <div className="key"><span className="k-forecast">Forecast</span><span className="k-upper">P90</span><span className="k-actual">Actual</span></div>
        </aside>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
