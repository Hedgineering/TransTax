"use client";
import React, { useState } from 'react';
import io from 'socket.io-client';

const Translate: React.FC = () => {
  const [sourceLanguage, setSrcLanguage] = useState('');
  const [sourceCurrency, setSrcCurrency] = useState('');
  const [destinationLanguage, setDestLanguage] = useState('');
  const [destinationCurrency, setDestCurrency] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!destinationLanguage || !destinationCurrency || !file) {
      alert('All fields are required');
      return;
    }

    // Establish WebSocket connection upon form submission
    const socket = io('http://localhost:5000', {
      transports: ['websocket'],
      reconnection: false
    });

    socket.on('connect', () => {
      console.log('Connected to the server');
      const CHUNK_SIZE = 1024 * 512; // 0.5MB
      const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
      const fileId = `${file.name}-${Date.now()}`; // Unique ID for the file upload

      for (let i = 0; i < totalChunks; i++) {
        const blob = file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE);
        const reader = new FileReader();
        reader.onload = (e) => {
          if(e.target?.result && typeof(e.target.result) == 'string') {
            const base64Content = e.target?.result?.split(',')[1];
            socket.emit('file_chunk', {
              fileId: fileId,
              chunkIndex: i,
              totalChunks: totalChunks,
              chunkData: base64Content,
              fileName: file.name
            });
          } else { console.log("File not in expected format.") }
        };
        reader.readAsDataURL(blob);
      }
      socket.emit('generate_pdfs', {
        sourceLanguage,
        sourceCurrency,
        destinationLanguage,
        destinationCurrency,
        fileName: file.name,
        fileId
      });
    });

    socket.on('hello', () => console.log('Server Hello Received.'))

    socket.on('pdf_ready', (data: { url: string }) => {
      console.log(`PDF ready: ${data.url}`);
      // Handle PDF URL (e.g., display it to the user)
    });

    socket.on('file_received', () => {
      console.log("Finished receiving file");
    });

    socket.on('job_finished', (data) => {
      console.log(`Job finished: ${JSON.stringify(data)}`);
      socket.off('job_finished')
      socket.off('pdf_ready')
      socket.disconnect();
    });
  };

  return (
    <div className="h-screen flex flex-col justify-center items-center">
      <header className="text-8xl font-serif font-bold mb-1">Transtax</header>
      <p className="text-xl mb-4">A Multilingual Invoice Generation Tool</p>
      <div className="max-w-md mx-auto my-10 bg-white p-8 border border-gray-200 rounded-lg shadow-lg">
        <h1 className="text-xl font-semibold mb-4">PDF Generation Form</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="srcLanguage" className="block mb-2 text-sm font-medium text-gray-900">Source Language</label>
            <select
              id="srcLanguage"
              value={sourceLanguage}
              onChange={e => setSrcLanguage(e.target.value)}
              className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5"
            >
              <option value="">Select Language</option>
              <option value="arabic">Arabic</option>
              <option value="english">English</option>
              <option value="japanese">Japanese</option>
            </select>
          </div>
          <div>
            <label htmlFor="srcCurrency" className="block mb-2 text-sm font-medium text-gray-900">Source Currency</label>
            <select
              id="srcCurrency"
              value={sourceCurrency}
              onChange={e => setSrcCurrency(e.target.value)}
              className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5"
            >
              <option value="">Select Currency</option>
              <option value="JPY">Japanese Yen</option>
              <option value="SAR">Saudi Riyal</option>
              <option value="AED">UAE Dirham</option>
              <option value="USD">US Dollar</option>
            </select>
          </div>
          <div>
            <label htmlFor="destLanguage" className="block mb-2 text-sm font-medium text-gray-900">Destination Language</label>
            <select
              id="destLanguage"
              value={destinationLanguage}
              onChange={e => setDestLanguage(e.target.value)}
              className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5"
            >
              <option value="">Select Language</option>
              <option value="arabic">Arabic</option>
              <option value="english">English</option>
              <option value="japanese">Japanese</option>
            </select>
          </div>
          <div>
            <label htmlFor="destCurrency" className="block mb-2 text-sm font-medium text-gray-900">Destination Currency</label>
            <select
              id="destCurrency"
              value={destinationCurrency}
              onChange={e => setDestCurrency(e.target.value)}
              className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5"
            >
              <option value="">Select Currency</option>
              <option value="JPY">Japanese Yen</option>
              <option value="SAR">Saudi Riyal</option>
              <option value="AED">UAE Dirham</option>
              <option value="USD">US Dollar</option>
            </select>
          </div>
          <div>
            <label htmlFor="file" className="block mb-2 text-sm font-medium text-gray-900">Invoice Data (CSV)</label>
            <input
              type="file"
              id="file"
              onChange={e => setFile(e.target.files ? e.target.files[0] : null)}
              className="block w-full text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 cursor-pointer focus:outline-none p-2.5"
            />
          </div>
          <button type="submit" className="w-full text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center">Submit</button>
        </form>
      </div>
      <div className="mt-4">
        <a href='/' className="text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-4 py-2">Home</a>
      </div>
    </div>
  );
};

export default Translate;
