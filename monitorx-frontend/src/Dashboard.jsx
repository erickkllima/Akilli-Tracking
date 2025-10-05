import { useEffect, useState } from "react";
import { getAnalytics } from "./api";
import { Pie, Bar, Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement, BarElement,
} from "chart.js";

ChartJS.register(
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement, BarElement
);

export default function Dashboard() {
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState("");
  const [canal, setCanal] = useState("");
  const [sentimento, setSentimento] = useState("");
  const [tag, setTag] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [data, setData] = useState({
    total: 0,
    by_sentiment: [],
    by_channel: [],
    timeseries_daily: [],
    top_tags: [],
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = {};
      if (q) params.q = q;
      if (canal) params.canal = canal;
      if (sentimento) params.sentimento = sentimento;
      if (tag) params.tag = tag;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const res = await getAnalytics(params);
      setData(res);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  // Sentimentos -> Pie
  const pieLabels = data.by_sentiment.map(s => s.sentimento);
  const pieValues = data.by_sentiment.map(s => s.count);

  const pieConfig = {
    labels: pieLabels,
    datasets: [{
      data: pieValues,
      // cores: manter consistência com badges
      backgroundColor: pieLabels.map(lbl => (
        lbl === "positivo" ? "#16a34a" :
        lbl === "neutro"   ? "#f59e0b" :
        lbl === "negativo" ? "#dc2626" : "#6b7280"
      )),
    }],
  };

  // Canais -> Bar
  const barLabels = data.by_channel.map(c => c.canal);
  const barValues = data.by_channel.map(c => c.count);
  const barConfig = {
    labels: barLabels,
    datasets: [{ label: "Menções por canal", data: barValues }],
  };

  // Timeseries -> Line
  const lineLabels = data.timeseries_daily.map(t => t.date);
  const lineValues = data.timeseries_daily.map(t => t.count);
  const lineConfig = {
    labels: lineLabels,
    datasets: [{ label: "Menções por dia", data: lineValues, tension: 0.2 }],
  };

  // Top tags -> Bar
  const tagsLabels = data.top_tags.map(t => t.tag);
  const tagsValues = data.top_tags.map(t => t.count);
  const tagsConfig = {
    labels: tagsLabels,
    datasets: [{ label: "Top tags", data: tagsValues }],
  };

  return (
    <div style={{ paddingTop: 10 }}>
      <h2>Dashboard Analítico</h2>

      {/* filtros */}
      <div style={{ display: "grid", gap: 8, gridTemplateColumns: "1fr 140px 140px 1fr 1fr auto" }}>
        <input placeholder="Texto..." value={q} onChange={(e)=>setQ(e.target.value)} />
        <select value={canal} onChange={(e)=>setCanal(e.target.value)}>
          <option value="">Canal (todos)</option>
          <option>Facebook</option>
          <option>Instagram</option>
          <option>YouTube</option>
          <option>LinkedIn</option>
          <option>X (Twitter)</option>
          <option>Blog</option>
          <option>Site</option>
        </select>
        <select value={sentimento} onChange={(e)=>setSentimento(e.target.value)}>
          <option value="">Sentimento (todos)</option>
          <option value="positivo">positivo</option>
          <option value="neutro">neutro</option>
          <option value="negativo">negativo</option>
        </select>
        <select value={dateField} onChange={(e)=>setDateField(e.target.value)}>
            <option value="mined">Data de mineração</option>
            <option value="published">Data de publicação</option>
        </select>
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        <input type="date" value={dateFrom} onChange={(e)=>setDateFrom(e.target.value)} />
        <input type="date" value={dateTo} onChange={(e)=>setDateTo(e.target.value)} />
        <button onClick={fetchData}>Aplicar</button>
      </div>

      {loading && <div style={{ margin: "10px 0" }}>Carregando…</div>}

      <div style={{ marginTop: 12, display: "grid", gap: 16, gridTemplateColumns: "1fr 1fr" }}>
        <div style={{ padding: 10, border: "1px solid #e5e7eb", borderRadius: 8 }}>
          <h3>Total de menções: {data.total}</h3>
          <Pie data={pieConfig} />
        </div>

        <div style={{ padding: 10, border: "1px solid #e5e7eb", borderRadius: 8 }}>
          <h3>Menções por canal</h3>
          <Bar data={barConfig} />
        </div>

        <div style={{ padding: 10, border: "1px solid #e5e7eb", borderRadius: 8 }}>
          <h3>Evolução diária</h3>
          <Line data={lineConfig} />
        </div>

        <div style={{ padding: 10, border: "1px solid #e5e7eb", borderRadius: 8 }}>
          <h3>Top tags</h3>
          <Bar data={tagsConfig} />
        </div>
      </div>
    </div>
  );
}
