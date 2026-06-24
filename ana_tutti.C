#include <TFile.h>
#include <TTree.h>
#include <TCanvas.h>
#include <TString.h>
#include <TSystem.h>
#include <iostream>

void PlotWaves(const char* filename, const char* folder) {
    
    TFile *f = TFile::Open(filename, "READ");
    if (!f || f->IsZombie()) {
        std::cerr << "Error: cannot open file " << filename << std::endl;
        return;
    }

    TTree *RawEvents = (TTree*)f->Get("RawEvents");
    if (!RawEvents) {
        std::cerr << "Error: Tree 'RawEvents' not found!" << std::endl;
        f->Close();
        return;
    }

    gSystem->mkdir(folder, kTRUE);

    gROOT->SetBatch(kTRUE);
    TCanvas *c1 = new TCanvas("c1", "Plot Canvas", 800, 600);

    // Limiti dei loop (8 board, 32 canali)
    const int numBoards = 8;
    const int numChannels = 32;

    // 5. Loop su Board e Canali
    for (int iBoard = 0; iBoard < numBoards; ++iBoard) {
        for (int iChannel = 0; iChannel < numChannels; ++iChannel) {
            
            // Formula il comando di Draw e il nome dell'istogramma temporaneo
            TString histName = Form("h_%d_%d", iBoard, iChannel);
            TString drawCmd = Form("Waves[%d][%d]:Iteration$>>%s(1024,0,1024,4096,0,4096)", iBoard, iChannel, histName.Data());
            
            std::cout << "Plottando Board " << iBoard << ", Canale " << iChannel << "..." << std::endl;
            
            // Disegna sul canvas con l'opzione zcol
            RawEvents->Draw(drawCmd, "", "zcol");

            // Definisci i path di output completi
            TString outPathPdf = Form("%s/zcol_%d_%d.pdf", folder, iBoard, iChannel);
            TString outPathRoot = Form("%s/zcol_%d_%d.root", folder, iBoard, iChannel);

            // Salva come PDF
            c1->SaveAs(outPathPdf);

            // Salva l'istogramma in un file .root dedicato
            TH2F *hTemp = (TH2F*)gDirectory->Get(histName);
            if (hTemp) {
                TFile *fOut = TFile::Open(outPathRoot, "RECREATE");
                hTemp->Write();
                fOut->Close();
            }
            
            // Pulisci il canvas per il plot successivo
            c1->Clear();
        }
    }

    // Chiudi tutto ed esci in modo pulito
    f->Close();
    delete c1;
    std::cout << "Fatto! Tutti i plot sono salvati nella cartella: " << folder << std::endl;
}
