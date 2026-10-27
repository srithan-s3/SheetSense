import { useRef, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  FileSpreadsheet,
  FolderOpen,
  LockKeyhole,
  UploadCloud,
  X,
} from "lucide-react";
import { SamplePicker } from "../components/SamplePicker";
import { Spinner } from "../components/UI";
import type { Sample, Session } from "../types";
export function validateFile(file: File): string | null {
  if (!/\.(xlsx|xls|csv)$/i.test(file.name))
    return "Choose an Excel (.xlsx or .xls) or CSV file.";
  if (!file.size)
    return "This file is empty. Choose a spreadsheet containing data.";
  const maxMB = Number(import.meta.env.VITE_MAX_UPLOAD_MB || 10);
  if (file.size > maxMB * 1024 * 1024)
    return `This file exceeds the ${maxMB} MB upload limit.`;
  return null;
}
export function UploadPage({
  upload,
  session,
  busy,
  onChoose,
  onSample,
  error,
  onClear,
}: {
  upload: (file: File) => Promise<void>;
  session: Session | null;
  busy: boolean;
  onChoose: (sheet: string) => void;
  onSample: (sample: Sample) => void;
  error: string;
  onClear: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState("");
  const [sheet, setSheet] = useState(session?.sheets[0] || "");
  function selectFile(next?: File) {
    if (!next || busy) return;
    const issue = validateFile(next);
    setValidation(issue || "");
    if (issue) return;
    setFile(next);
    void upload(next);
  }
  const selectedSheet = session?.sheets.includes(sheet)
    ? sheet
    : session?.sheets[0] || "";
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">GOOD INSIGHTS START HERE</span>
          <h1>Meet your data’s potential.</h1>
          <p>Upload a spreadsheet. We’ll help you see it in a new light.</p>
        </div>
        <span className="tag">
          <LockKeyhole size={13} />
          Private by design
        </span>
      </div>
      <div className="upload-layout">
        <section className="upload-card">
          <div className="card-title">
            <span className="step-pill">01</span>
            <div>
              <h2>Bring your spreadsheet</h2>
              <p>Excel or CSV — you’re in the right place.</p>
            </div>
          </div>
          <div
            className={`dropzone ${dragging ? "dragging" : ""} ${busy ? "processing" : ""}`}
            onDragOver={(event) => {
              event.preventDefault();
              if (!busy) setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              selectFile(event.dataTransfer.files[0]);
            }}
          >
            <input
              ref={input}
              type="file"
              accept=".xlsx,.xls,.csv"
              aria-label="Upload spreadsheet"
              onChange={(event) => selectFile(event.target.files?.[0])}
              disabled={busy}
              className="sr-only"
            />
            <span className="upload-cloud">
              <UploadCloud size={30} strokeWidth={1.6} />
            </span>
            {busy ? (
              <>
                <h3>Your data is on its way.</h3>
                <Spinner label="Uploading and reading your file…" />
              </>
            ) : (
              <>
                <h3>Drop your spreadsheet here</h3>
                <p>or choose a file from your computer</p>
                <button
                  className="button primary"
                  onClick={() => input.current?.click()}
                >
                  <FolderOpen size={17} />
                  Browse files
                </button>
                <small>
                  .XLSX, .XLS, .CSV · up to{" "}
                  {import.meta.env.VITE_MAX_UPLOAD_MB || 10} MB
                </small>
              </>
            )}
          </div>
          {file && (
            <div className="selected-file">
              <span className="dataset-icon">
                <FileSpreadsheet size={21} />
              </span>
              <div>
                <strong>{file.name}</strong>
                <small>
                  {(file.size / 1024).toFixed(1)} KB
                  {!busy && session?.filename === file.name
                    ? " · Ready to preview"
                    : ""}
                </small>
              </div>
              <button
                className="icon-button"
                disabled={busy}
                aria-label="Clear selected file"
                onClick={() => {
                  setFile(null);
                  setValidation("");
                  onClear();
                  if (input.current) input.current.value = "";
                }}
              >
                <X size={17} />
              </button>
            </div>
          )}
          {(validation || error) && (
            <p role="alert" className="inline-error">
              {validation || error}
            </p>
          )}
          {session && !busy && !error && (
            <div className="sheet-selection">
              <div>
                <CheckCircle2 size={19} />
                <strong>{session.filename} is ready</strong>
              </div>
              <label className="field" htmlFor="worksheet">
                <span>Choose a worksheet</span>
                <select
                  id="worksheet"
                  value={selectedSheet}
                  onChange={(event) => setSheet(event.target.value)}
                >
                  {session.sheets.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="button primary"
                disabled={!selectedSheet}
                onClick={() => onChoose(selectedSheet)}
              >
                Preview your data
                <ArrowRight size={17} />
              </button>
            </div>
          )}
        </section>
        <aside className="upload-aside">
          <span className="feature-icon">
            <FileSpreadsheet size={23} />
          </span>
          <h2>
            A little preparation.
            <br />
            Better insights.
          </h2>
          <ul>
            <li>
              <CheckCircle2 size={17} />
              <span>Give each column a clear header in the first row.</span>
            </li>
            <li>
              <CheckCircle2 size={17} />
              <span>Keep one record per row and one value per cell.</span>
            </li>
            <li>
              <CheckCircle2 size={17} />
              <span>
                Mixed data? We’ll flag quality issues to help you make sense of
                them.
              </span>
            </li>
          </ul>
          <div className="privacy-box">
            <LockKeyhole size={19} />
            <p>
              Files are stored temporarily on this server. You can delete your
              session anytime. Your data isn’t sent to AI services.
            </p>
          </div>
        </aside>
      </div>
      <SamplePicker onSelect={onSample} busy={busy} />
    </>
  );
}
