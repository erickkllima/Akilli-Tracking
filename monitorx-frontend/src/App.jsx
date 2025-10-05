import { useState } from "react";
import MentionsTable from "./MentionsTable";
import Dashboard from "./Dashboard";
import { runSearch } from "./api";

export default function App() {
  const [term, setTerm] = useState("");
  const [qty, setQty] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [refreshTick, setRefreshTick] = useState(0);
  const [enrichDates, setEnrichDates] = useState(true);
  const [view, setView] = useState("table"); // "table" | "dashboard"

  const handleSearch = async () => {
    if (!term) { alert("Digite um termo"); return; }
    await runSearch(term, qty || undefined, dateFrom || undefined, dateTo || undefined, erichDates);
    setRefreshTick((n) => n + 1);
    alert("Busca concluída! Dados atualizados.");
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>Akilli Tracking — MVP</h1>

      {/* barra superior */}
      <label style={{ display:"flex", alignItems:"center", gap:6 }}>
        <input
          type="checkbox"
          checked={enrichDates}
          onChange={(e)=>setEnrichDates(e.target.checked)}
        />
        Coletar data de publicação
      </label>

      <div style={{ display: "grid", gap: 8, gridTemplateColumns: "1.6fr 0.6fr 1fr 1fr auto auto" }}>
        <input placeholder="Termo (ex.: Akilli Brasil)" value={term} onChange={(e)=>setTerm(e.target.value)} />
        <input type="number" min={1} max={100} value={qty} onChange={(e)=>setQty(e.target.value ? +e.target.value : "")} placeholder="Limite" />
        <input type="date" value={dateFrom} onChange={(e)=>setDateFrom(e.target.value)} />
        <input type="date" value={dateTo} onChange={(e)=>setDateTo(e.target.value)} />
        <button onClick={handleSearch}>Rodar busca e salvar</button>
        <div style={{ display:"flex", gap:8 }}>
          <button onClick={()=>setView("table")} disabled={view==="table"}>Tabela</button>
          <button onClick={()=>setView("dashboard")} disabled={view==="dashboard"}>Dashboard</button>
        </div>
      </div>

      {view === "table" ? (
        <MentionsTable refreshTick={refreshTick} />
      ) : (
        <Dashboard />
      )}
    </div>
  );
}
