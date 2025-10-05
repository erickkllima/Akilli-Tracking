import axios from "axios";

const API = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

export const getMentions = async (params = {}) => {
  const res = await API.get("/mentions", { params });
  return res.data;
};

export const runSearch = async (term, qty, dateFrom, dateTo, enrichDates) => {
  const params = { term };
  if (qty) params.qty = qty;
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;
  if (enrichDates) params.enrich_dates = true;
  const res = await API.post("/search", null, { params });
  return res.data;
};

export const updateTags = async (id, tags) => {
  const res = await API.patch(`/mentions/${id}/tags`, { add: tags });
  return res.data;
};

export const deleteMention = async (id) => {
  const res = await API.delete(`/mentions/${id}`);
  return res.status; // 204 esperado
};

export const bulkDeleteMentions = async (ids) => {
  const res = await API.post("/mentions/bulk_delete", { ids });
  return res.data; // { deleted: N }
};

export const getAnalytics = async (params = {}) => {
  const res = await API.get("/analytics", { params });
  return res.data; // { total, by_sentiment, by_channel, timeseries_daily, top_tags }
};
