import { useState, useEffect, useMemo } from "react";
import { getMentions, updateTags, deleteMention, bulkDeleteMentions } from "./api";

// Badge de sentimento (botão não clicável, arredondado, texto branco em negrito)
function SentimentBadge({ value }) {
  const map = {
    positivo: "#16a34a", // verde
    neutro:   "#f59e0b", // amarelo
    negativo: "#dc2626", // vermelho
  };
  const bg = map[value] || "#6b7280"; // fallback cinza

  return (
    <button
      disabled
      style={{
        backgroundColor: bg,
        color: "#fff",
        fontWeight: 700,
        border: "none",
        borderRadius: "9999px",
        padding: "4px 10px",
        cursor: "default",
        textTransform: "capitalize",
      }}
    >
      {value}
    </button>
  );
}

export default function MentionsTable({ refreshTick = 0 }) {
  const [mentions, setMentions] = useState([]);

  // Filtros básicos
  const [q, setQ] = useState("");
  const [canal, setCanal] = useState("");
  const [sentimento, setSentimento] = useState("");
  const [tag, setTag] = useState("");

  // Filtro por data (campo e range)
  const [dateField, setDateField] = useState("published"); // 'mined' | 'published'
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [loading, setLoading] = useState(false);

  // paginação
  const [page, setPage] = useState(1);
  const limit = 100; // máximo 100 por página
  const [total, setTotal] = useState(0);
  const [pageCount, setPageCount] = useState(1);

  // seleção (persistente entre páginas)
  const [selectedIds, setSelectedIds] = useState(new Set());

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = { limit, page, date_field: dateField };
      if (q) params.q = q;
      if (canal) params.canal = canal;
      if (sentimento) params.sentimento = sentimento;
      if (tag) params.tag = tag;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const data = await getMentions(params);
      setMentions(data.items || []);
      setTotal(data.total || 0);
      setPageCount(data.page_count || 1);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);
  useEffect(() => { fetchData(); }, [refreshTick, page]);

  const handleApplyFilters = () => {
    setPage(1); // volta para a primeira página ao aplicar filtros
    fetchData();
  };

  const handleAddTag = async (id) => {
    const t = prompt("Digite a nova tag:");
    if (t) {
      await updateTags(id, [t]);
      fetchData();
    }
  };

  const handleDelete = async (id) => {
    const ok = confirm(`Tem certeza que deseja excluir a menção #${id}?`);
    if (!ok) return;
    await deleteMention(id);
    // remove da seleção, se estiver
    setSelectedIds(prev => {
      const ns = new Set(prev);
      ns.delete(id);
      return ns;
    });
    // Se a página ficar sem itens após deletar, tenta voltar uma página
    if (mentions.length === 1 && page > 1) {
      setPage((p) => p - 1);
    } else {
      fetchData();
    }
  };

  // Seleção da página atual
  const pageIds = useMemo(() => new Set(mentions.map(m => m.id)), [mentions]);
  const allPageSelected = useMemo(
    () => mentions.length > 0 && mentions.every(m => selectedIds.has(m.id)),
    [mentions, selectedIds]
  );
  const somePageSelected = useMemo(
    () => mentions.some(m => selectedIds.has(m.id)) && !allPageSelected,
    [mentions, selectedIds, allPageSelected]
  );

  const toggleSelectAllPage = () => {
    setSelectedIds(prev => {
      const ns = new Set(prev);
      if (allPageSelected) {
        mentions.forEach(m => ns.delete(m.id));
      } else {
        mentions.forEach(m => ns.add(m.id));
      }
      return ns;
    });
  };

  const toggleOne = (id) => {
    setSelectedIds(prev => {
      const ns = new Set(prev);
      if (ns.has(id)) ns.delete(id); else ns.add(id);
      return ns;
    });
  };

  const clearSelection = () => setSelectedIds(new Set());

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      alert("Nenhuma menção selecionada.");
      return;
    }
    const ok = confirm(`Excluir ${ids.length} menção(ões)? Esta ação não pode ser desfeita.`);
    if (!ok) return;
    const res = await bulkDeleteMentions(ids);
    // limpa seleção dos que foram excluídos
    setSelectedIds(prev => {
      const ns = new Set(prev);
      ids.forEach(id => ns.delete(id));
      return ns;
    });
    // se a página ficar sem itens, tenta voltar uma página
    if (mentions.length === ids.filter(id => pageIds.has(id)).length && page > 1) {
      setPage((p) => p - 1);
    } else {
      fetchData();
    }
    alert(`Excluídas: ${res.deleted}`);
  };

  const canPrev = page > 1;
  const canNext = page < pageCount;
  const selectedCount = selectedIds.size;

  // rótulo dinâmico da coluna de data
  const dateColLabel = dateField === "published" ? "Data de publicação" : "Minerado em";

  return (
    <div style={{ marginTop: 16 }}>
      {/* Filtros */}
      <div
        style={{
          display: "grid",
          gap: 8,
          gridTemplateColumns: "1fr 180px 180px 1fr auto",
        }}
      >
        <input
          placeholder="Filtrar por texto..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select value={canal} onChange={(e) => setCanal(e.target.value)}>
          <option value="">Canal (todos)</option>
          <option>Facebook</option>
          <option>Instagram</option>
          <option>YouTube</option>
          <option>LinkedIn</option>
          <option>X (Twitter)</option>
          <option>Blog</option>
          <option>Site</option>
        </select>
        <select
          value={sentimento}
          onChange={(e) => setSentimento(e.target.value)}
        >
          <option value="">Sentimento (todos)</option>
          <option value="positivo">positivo</option>
          <option value="neutro">neutro</option>
          <option value="negativo">negativo</option>
        </select>
        <input
          placeholder="Filtrar por tag..."
          value={tag}
          onChange={(e) => setTag(e.target.value)}
        />
        <button onClick={handleApplyFilters}>Aplicar filtros</button>
      </div>

      {/* Filtros de data */}
      <div style={{ marginTop: 8, display: "grid", gap: 8, gridTemplateColumns: "180px 1fr 1fr" }}>
        <select value={dateField} onChange={(e)=>setDateField(e.target.value)}>
          <option value="published">Data de publicação</option>
          <option value="mined">Data de mineração</option>
        </select>
        <input type="date" value={dateFrom} onChange={(e)=>setDateFrom(e.target.value)} />
        <input type="date" value={dateTo} onChange={(e)=>setDateTo(e.target.value)} />
      </div>

      {/* Toolbar de seleção/bulk */}
      <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <input
            type="checkbox"
            checked={allPageSelected}
            ref={el => { if (el) el.indeterminate = somePageSelected; }}
            onChange={toggleSelectAllPage}
          />
          Selecionar página
        </label>

        <button
          onClick={handleBulkDelete}
          disabled={selectedCount === 0}
          style={{
            background: selectedCount ? "#ef4444" : "#f3f4f6",
            color: selectedCount ? "#fff" : "#6b7280",
            border: "none",
            padding: "6px 10px",
            borderRadius: 6,
            cursor: selectedCount ? "pointer" : "not-allowed",
          }}
        >
          Excluir selecionados ({selectedCount})
        </button>

        {selectedCount > 0 && (
          <button
            onClick={clearSelection}
            style={{ border: "1px solid #d1d5db", padding: "6px 10px", borderRadius: 6 }}
          >
            Limpar seleção
          </button>
        )}

        <span style={{ marginLeft: "auto" }}>
          Página {page} de {pageCount} — {total} menções
        </span>
      </div>

      {loading && <div style={{ marginTop: 8 }}>Carregando…</div>}

      {/* Tabela */}
      <table
        border="1"
        cellPadding="6"
        style={{ marginTop: 12, width: "100%", borderCollapse: "collapse" }}
      >
        <thead>
          <tr>
            <th style={{ width: 36 }}></th>
            <th>ID</th>
            <th>Título</th>
            <th>Canal</th>
            <th>Sentimento</th>
            <th>Tags</th>
            <th style={{ width: 200 }}>Ações</th>
            <th style={{ width: 180 }}>{dateColLabel}</th>
          </tr>
        </thead>
        <tbody>
          {mentions.map((m) => (
            <tr key={m.id}>
              <td style={{ textAlign: "center" }}>
                <input
                  type="checkbox"
                  checked={selectedIds.has(m.id)}
                  onChange={() => toggleOne(m.id)}
                />
              </td>
              <td>{m.id}</td>
              <td>
                <a href={m.url} target="_blank" rel="noreferrer">
                  {m.titulo}
                </a>
              </td>
              <td>{m.canal}</td>
              <td><SentimentBadge value={m.sentimento} /></td>
              <td>{m.tags.join(", ")}</td>
              <td>
                <button onClick={() => handleAddTag(m.id)} style={{ marginRight: 8 }}>
                  + Tag
                </button>
                <button
                  onClick={() => handleDelete(m.id)}
                  style={{
                    background: "#ef4444",
                    color: "#fff",
                    border: "none",
                    padding: "6px 10px",
                    borderRadius: 6,
                  }}
                >
                  Excluir
                </button>
              </td>
              <td>
                {(() => {
                  const val = dateField === "published" ? m.published_at : m.created_at;
                  return val ? new Date(val).toLocaleString() : "—";
                })()}
              </td>
            </tr>
          ))}
          {mentions.length === 0 && !loading && (
            <tr>
              <td colSpan="8">Nenhum resultado.</td>
            </tr>
          )}
        </tbody>
      </table>

      {/* paginação */}
      <div style={{ marginTop: 8, display: "flex", gap: 12, alignItems: "center" }}>
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
          ◀ Anterior
        </button>
        <button onClick={() => setPage((p) => Math.min(pageCount, p + 1))} disabled={page >= pageCount}>
          Próxima ▶
        </button>
        <span style={{ marginLeft: "auto" }}>
          Página {page} de {pageCount} — {total} menções
        </span>
      </div>
    </div>
  );
}
