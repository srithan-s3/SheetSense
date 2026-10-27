# SheetSense implementation contract

All JSON responses: `{success:true,data:...}` or `{success:false,error:{code,message}}`.
Requests for a session require `X-Session-Token` from upload. CORS allows that header.
`POST /api/upload` multipart `file` -> `{session_id,token,filename,sheets:[string],expires_at}`. No analysis until sheet is chosen.
`GET /api/sheets/:id` -> `{sheets:[string]}`.
`GET /api/samples` -> `[{id,name,description,filename}]`; `GET /api/samples/:id` downloads synthetic file. Client fetches blob then uploads via regular upload pipeline.
`POST /api/analyze/:id` and `/api/filter/:id` body `{sheet,filters:{column:{values?:string[],min?:number,max?:number,start?:string,end?:string}},version?:"original"|"cleaned"}` -> Analysis below.
`POST /api/preview/:id` same body plus `{page:1,page_size:25,search:""}` -> `{columns:Column[],rows:Record<string,unknown>[],total_rows,page,page_size,total_pages}`. Search covers all filtered records on backend.
`POST /api/custom-chart/:id` same body plus `{x,y?,y2?,type,aggregation:"sum"|"mean"|"count"|"min"|"max"|"median",sort:"asc"|"desc"|"label",top_n:10}` -> Chart. `y2` supplies the second numeric series for a stacked bar.
`POST /api/clean/:id` body `{sheet,operations:[{action:"drop_duplicates"}|{action:"fill_numeric",column,method:"mean"|"median"|"zero"}|{action:"fill_category",column,method:"mode"|"unknown"}],apply:false|true}` -> `{before_rows,after_rows,changed_cells,preview:Record[],version:"original"|"cleaned"}`. Always derives from original; apply false previews. No original mutation.
`POST /api/export/:id` same analysis body plus `{format:"pdf"|"csv"|"xlsx"}` -> download binary with Content-Disposition. POST carries current filters, avoiding hidden last-analysis state. GET supports unfiltered original `?format=...&sheet=...`.
`POST /api/delete/:id` -> `{deleted:true}`.

Preview pages contain 1–100 rows and search text is limited to 200 characters.
Cleaning plans contain 1–30 operations; one cleaned worksheet is retained per
session. A later application replaces that working copy and preserves all original sheets.

## Analysis
```
{filename,sheet,version,rows,total_rows,column_count,analyzed_at,
 columns:Column[], kpis:[{label,value:number|string,description,format?:"number"|"decimal"|"percent"}],
 charts:Chart[], insights:[{title,text,kind:"info"|"positive"|"warning"}],
 quality:{missing_cells,missing_percent,duplicate_rows,issues:[{column?,type,severity:"info"|"warning",message,count?}]},
 filters:[{column,type:"category"|"date"|"numeric",options?:string[],min?:number|string,max?:number|string}],
 notes:string[]}
Column = {name,type:"numeric"|"category"|"date"|"text",missing,unique}
Chart = {id,type:"bar"|"horizontal_bar"|"line"|"pie"|"doughnut"|"histogram"|"scatter"|"stacked_bar",title,description,x_label,y_label,x_key:string,y_keys:string[],series_labels?:Record<string,string>,data:Record<string,unknown>[],alternatives:string[]}
```

## Backend module contract
`app.analytics.engine`: `prepare_frame(raw:DataFrame)->(typed_frame, columns, issues)`; `apply_filters(frame, columns, filters)->DataFrame`; `analyze_frame(raw, filename, sheet, filters=None, version="original")->dict`; `preview_frame(raw, filters=None, page=1,page_size=25,search="")->dict`; `custom_chart(raw,config,filters=None)->Chart`.
Validation failures raise ValueError with a safe readable message. Engine does not handle session/files/routes. API owns storage, parsing, validation and cleanup. API imports engine functions. Dates: native Excel dates or unambiguous ISO only; ambiguous strings remain text/category and issue is reported. Identifier columns excluded from automatic numeric metrics. All responses finite/JSON-safe.
