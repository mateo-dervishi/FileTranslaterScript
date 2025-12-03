"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";

type ProcessingStatus = "idle" | "uploading" | "processing" | "complete" | "error";

interface ProcessingState {
  status: ProcessingStatus;
  progress: number;
  message: string;
  downloadUrl?: string;
  fileName?: string;
}

export default function Home() {
  const [state, setState] = useState<ProcessingState>({
    status: "idle",
    progress: 0,
    message: "",
  });

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setState({
        status: "error",
        progress: 0,
        message: "Please upload a PDF file",
      });
      return;
    }

    setState({
      status: "uploading",
      progress: 10,
      message: "Uploading catalogue...",
    });

    try {
      const formData = new FormData();
      formData.append("file", file);

      setState({
        status: "processing",
        progress: 20,
        message: "Analyzing document...",
      });

      const response = await fetch("/api/translate", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        // Try to parse as JSON, fallback to status text
        let errorMessage = "Translation failed";
        try {
          const contentType = response.headers.get("content-type");
          if (contentType && contentType.includes("application/json")) {
            const error = await response.json();
            errorMessage = error.error || errorMessage;
          } else {
            const text = await response.text();
            errorMessage = text || `Server error: ${response.status}`;
          }
        } catch {
          errorMessage = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      // Get the blob from response
      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const originalName = file.name.replace(".pdf", "");

      setState({
        status: "complete",
        progress: 100,
        message: "Translation complete!",
        downloadUrl,
        fileName: `${originalName}_ENGLISH.pdf`,
      });
    } catch (error) {
      setState({
        status: "error",
        progress: 0,
        message: error instanceof Error ? error.message : "An error occurred",
      });
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
    },
    maxFiles: 1,
    disabled: state.status === "uploading" || state.status === "processing",
  });

  const resetState = () => {
    if (state.downloadUrl) {
      URL.revokeObjectURL(state.downloadUrl);
    }
    setState({
      status: "idle",
      progress: 0,
      message: "",
    });
  };

  return (
    <main className="min-h-screen relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-20 left-10 text-[200px] chinese-char text-ink-100 select-none animate-pulse-soft">
          文
        </div>
        <div className="absolute bottom-20 right-10 text-[200px] chinese-char text-ink-100 select-none animate-pulse-soft" style={{ animationDelay: "1.5s" }}>
          译
        </div>
        <div className="absolute top-1/2 left-1/4 text-[100px] chinese-char text-ink-50 select-none opacity-50">
          翻
        </div>
        <div className="absolute top-1/3 right-1/4 text-[80px] chinese-char text-ink-50 select-none opacity-30">
          转
        </div>
      </div>

      {/* Main content */}
      <div className="relative z-10 container mx-auto px-4 py-12 md:py-20">
        {/* Header */}
        <motion.header 
          className="text-center mb-16"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <h1 className="text-5xl md:text-7xl font-light tracking-tight text-ink-950 mb-4">
            <span className="chinese-char">文译</span>{" "}
            <span className="text-vermillion-600">Wényì</span>
          </h1>
          <p className="text-xl md:text-2xl text-ink-500 font-light max-w-2xl mx-auto">
            Transform Chinese catalogues into English
            <br />
            <span className="text-ink-400">while preserving every detail</span>
          </p>
        </motion.header>

        {/* Upload area */}
        <motion.div
          className="max-w-2xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <AnimatePresence mode="wait">
            {state.status === "idle" || state.status === "error" ? (
              <motion.div
                key="dropzone"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3 }}
              >
                <div
                  {...getRootProps()}
                  className={`
                    relative cursor-pointer rounded-2xl border-2 border-dashed 
                    transition-all duration-300 ease-out
                    ${isDragActive 
                      ? "border-vermillion-500 bg-vermillion-50 scale-[1.02]" 
                      : "border-ink-200 hover:border-ink-300 bg-white/50 hover:bg-white/80"
                    }
                  `}
                >
                  <input {...getInputProps()} />
                  <div className="p-12 md:p-20 text-center">
                    <div className={`
                      w-20 h-20 mx-auto mb-6 rounded-full flex items-center justify-center
                      transition-colors duration-300
                      ${isDragActive ? "bg-vermillion-100" : "bg-ink-100"}
                    `}>
                      <svg 
                        className={`w-10 h-10 transition-colors duration-300 ${isDragActive ? "text-vermillion-600" : "text-ink-400"}`}
                        fill="none" 
                        viewBox="0 0 24 24" 
                        stroke="currentColor"
                      >
                        <path 
                          strokeLinecap="round" 
                          strokeLinejoin="round" 
                          strokeWidth={1.5} 
                          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" 
                        />
                      </svg>
                    </div>
                    <p className={`text-lg md:text-xl font-light transition-colors duration-300 ${isDragActive ? "text-vermillion-700" : "text-ink-600"}`}>
                      {isDragActive ? "Drop your catalogue here" : "Drag & drop your PDF catalogue"}
                    </p>
                    <p className="mt-2 text-ink-400">
                      or <span className="text-vermillion-600 hover:text-vermillion-700 underline underline-offset-4">browse files</span>
                    </p>
                    <p className="mt-6 text-sm text-ink-300">
                      Supports PDF files up to 100MB
                    </p>
                  </div>
                </div>

                {state.status === "error" && (
                  <motion.p
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-4 text-center text-vermillion-600"
                  >
                    {state.message}
                  </motion.p>
                )}
              </motion.div>
            ) : state.status === "uploading" || state.status === "processing" ? (
              <motion.div
                key="processing"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3 }}
                className="file-card rounded-2xl border border-ink-200 p-12 md:p-16 text-center"
              >
                <div className="w-20 h-20 mx-auto mb-6 relative">
                  <svg className="w-20 h-20 animate-spin text-ink-200" viewBox="0 0 24 24">
                    <circle 
                      className="opacity-25" 
                      cx="12" 
                      cy="12" 
                      r="10" 
                      stroke="currentColor" 
                      strokeWidth="2"
                      fill="none"
                    />
                    <path 
                      className="text-vermillion-500" 
                      fill="currentColor" 
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                </div>
                <p className="text-xl font-light text-ink-700 mb-2">{state.message}</p>
                <p className="text-ink-400 mb-6">This may take a few minutes for large catalogues</p>
                
                {/* Progress bar */}
                <div className="w-full h-2 bg-ink-100 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full progress-bar rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${state.progress}%` }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
                <p className="mt-3 text-sm text-ink-400">{state.progress}% complete</p>
              </motion.div>
            ) : state.status === "complete" ? (
              <motion.div
                key="complete"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3 }}
                className="file-card rounded-2xl border border-ink-200 p-12 md:p-16 text-center"
              >
                <div className="w-20 h-20 mx-auto mb-6 bg-green-100 rounded-full flex items-center justify-center">
                  <svg className="w-10 h-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-2xl font-light text-ink-700 mb-2">Translation Complete!</p>
                <p className="text-ink-400 mb-8">Your translated catalogue is ready</p>
                
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                  <a
                    href={state.downloadUrl}
                    download={state.fileName}
                    className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-vermillion-600 text-white rounded-xl hover:bg-vermillion-700 transition-colors font-medium"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download PDF
                  </a>
                  <button
                    onClick={resetState}
                    className="inline-flex items-center justify-center gap-2 px-8 py-4 border border-ink-200 text-ink-600 rounded-xl hover:bg-ink-50 transition-colors"
                  >
                    Translate Another
                  </button>
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </motion.div>

        {/* Features */}
        <motion.div
          className="mt-20 md:mt-32 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <Feature
            icon={
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
              </svg>
            }
            title="Chinese → English"
            description="Accurately translates all Chinese text while keeping English untouched"
          />
          <Feature
            icon={
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
              </svg>
            }
            title="Layout Preserved"
            description="Maintains original design, images, and backgrounds perfectly"
          />
          <Feature
            icon={
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            }
            title="High Quality"
            description="Output files maintain maximum quality for professional use"
          />
        </motion.div>

        {/* Footer */}
        <motion.footer
          className="mt-20 text-center text-ink-400 text-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          <p>Built by Mateo Dervishi</p>
        </motion.footer>
      </div>
    </main>
  );
}

function Feature({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="text-center p-6">
      <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-vermillion-50 flex items-center justify-center text-vermillion-600">
        {icon}
      </div>
      <h3 className="text-lg font-medium text-ink-800 mb-2">{title}</h3>
      <p className="text-ink-500 font-light">{description}</p>
    </div>
  );
}

