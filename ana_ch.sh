ib=$2
ic=$3
folder=$4

root $1 << EOF
  gROOT->SetBatch(kTRUE)
  new TCanvas("c", "c")
  RawEvents->Draw("Waves[$ib][$ic]:Iteration$>>(1024, 0, 1024, 4096, 0, 4096)", "", "zcol")
  c->SaveAs("$folder/zcol_${ib}_${ic}.pdf")
  c->SaveAs("$folder/zcol_${ib}_${ic}.root")
EOF
