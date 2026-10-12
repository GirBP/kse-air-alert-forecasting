import {completedHistory,parseTimestamp,ForecastError} from './forecast-core.mjs';
// Conservative website adaptation of the empirical K0 formula: history is frozen
// at onset, unlike v4 K0 which updates completed history at each landmark.
// No v4 score is attributed to this adaptation.
export function estimateRemaining({rows,originUtc,elapsedMinutes,nowUtc,boundaryUtc}) {
 const start=parseTimestamp(originUtc),now=parseTimestamp(nowUtc),boundary=parseTimestamp(boundaryUtc);
 if(!Number.isFinite(elapsedMinutes)||elapsedMinutes<0||!Number.isInteger(elapsedMinutes))throw new ForecastError('elapsed','Enter a nonnegative whole number of elapsed minutes.');
 const asof=start+elapsedMinutes*60000;
 if(!Number.isFinite(asof)||asof>now)throw new ForecastError('future_assessment','Assessment time is in the future.');
 if(asof>=boundary)return {status:'stale_snapshot',prediction_minutes:null,asof_utc:new Date(asof).toISOString()};
 const {history}=completedHistory(rows,start);
 const residuals=history.map(r=>r.duration).filter(d=>d>elapsedMinutes).map(d=>d-elapsedMinutes).sort((a,b)=>a-b);
 const n=residuals.length,mid=Math.floor(n/2);
 return {status:n>=5?'predicted':'insufficient_tail_support',method:'empirical_K0_onset_frozen_history',prediction_minutes:n>=5?(n%2?residuals[mid]:(residuals[mid-1]+residuals[mid])/2):null,eligible_n:n,completed_history_n:history.length,elapsed_minutes:elapsedMinutes,asof_utc:new Date(asof).toISOString()};
}
