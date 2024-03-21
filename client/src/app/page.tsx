"use client";
import React from 'react';
import Translate from "./translate/page";

const LandingPage: React.FC = () => {
  return (
    <div className="h-screen flex flex-col justify-center items-center">
      <header className="text-8xl font-serif font-bold mb-1">Transtax</header>
      <p className="text-xl mb-4">A Multilingual Invoice Generation Tool</p>
      <section className="w-1/2 bg-green-200 text-black p-8 rounded-lg shadow-md">
        <p className="text-lg mb-4">
          Transtax Multilingual & Currency Software is an innovative solution
          designed to streamline international business transactions through
          sophisticated translation and currency conversion tools. This project
          tackles the challenge of accurately translating complex financial
          documents, such as tax documentation and invoices, which demands
          precise understanding of financial terminology and context-specific
          nuances.
        </p>
        <p className="text-lg">
          Additionally, it addresses the need for real-time currency
          conversion in cross-border transactions. Our software is equipped
          with advanced features to ensure seamless communication and accuracy
          in translation, making it an indispensable tool for businesses
          operating in global markets.
        </p>
      </section>
      <div className="mt-4">
        <a href='/translate' className="text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-4 py-2">Translate</a>
      </div>
    </div>
  );
};

export default LandingPage;
