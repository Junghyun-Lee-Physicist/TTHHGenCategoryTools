// -*- C++ -*-
// =============================================================================
// plotTtbarCompare
// =============================================================================
// Overlays the genTtbarId sub-code distribution from a extend file hist file and a
// nano hist file (both produced by makeTtbarHist (this project)) and draws a ratio panel
// (extend file / nano).  If extend file and nano were run over the same event set the
// two curves must coincide and the ratio must be 1.0 in every populated bin.
//
// Also overlays, on the same canvas (different pad), the extend file Expanded_genTtbarId
// sub-code so the reclassification into 61/62/71/72 is visible against the
// nano genTtbarId (whose >= 2-add-b-jet events all sit in 53/54/55).
//
// Inputs are the histogram files written by makeTtbarHist:
//   nano file     must contain h_genTtbarId_sub
//   extend file file  must contain h_genTtbarId_sub (and h_Expanded_sub)
//
// Usage:
//   plotTtbarCompare --match match_TTHHto4b.root
//                    --nano    hist_nano_TTHHto4b.root
//                    --out     TTHHto4b_ttbarId_compare.png
//                    [--label TTHHto4b] [--normalize] [--logy]
//
// --normalize : scale both to unit area before comparing (use when extend file and
//               nano cover different event counts; compares shape only).
// =============================================================================

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>

#include <TCanvas.h>
#include <TFile.h>
#include <TH1.h>
#include <TLegend.h>
#include <TLatex.h>
#include <TLine.h>
#include <TPad.h>
#include <TStyle.h>

namespace {

struct Args {
  std::string extend, nano, out, label;
  std::string match;          // single match file from matchTtbarId --out
  bool normalize = false;
  bool logy = false;
};

[[noreturn]] void usage(int code) {
  std::cout <<
    "plotTtbarCompare\n"
    "  Two input modes:\n"
    "  (A) separate hist files from makeTtbarHist:\n"
    "      --extend file PATH   hist file from makeTtbarHist --mode extend file\n"
    "      --nano PATH      hist file from makeTtbarHist --mode nano\n"
    "  (B) a single match file from matchTtbarId --out:\n"
    "      --match PATH     holds h_genTtbarId_sub (nano), h_extend_genTtbarId_sub,\n"
    "                       h_extend_Expanded_sub, all over matched events\n"
    "  --out PATH       output image (.png/.pdf/.root by extension)\n"
    "  --label NAME     process label for titles (default derived from --out)\n"
    "  --normalize      scale all to unit area (shape-only comparison)\n"
    "  --logy           log scale on the main pad\n"
    "  -h, --help       this help\n";
  std::exit(code);
}

Args parseArgs(int argc, char** argv) {
  Args a;
  auto need = [&](int& i, const char* o) {
    if (i + 1 >= argc) { std::cerr << "ERROR: " << o << " needs a value\n"; std::exit(2); }
    return std::string(argv[++i]);
  };
  for (int i = 1; i < argc; ++i) {
    std::string s = argv[i];
    if      (s == "--extend" || s == "--sidecar")   a.extend = need(i, "--extend");
    else if (s == "--nano")      a.nano    = need(i, "--nano");
    else if (s == "--match")     a.match   = need(i, "--match");
    else if (s == "--out")       a.out     = need(i, "--out");
    else if (s == "--label")     a.label   = need(i, "--label");
    else if (s == "--normalize") a.normalize = true;
    else if (s == "--logy")      a.logy    = true;
    else if (s == "-h" || s == "--help") usage(0);
    else { std::cerr << "ERROR: unknown arg '" << s << "'\n"; usage(2); }
  }
  if (!a.match.empty()) {
    if (a.out.empty()) { std::cerr << "ERROR: --out is required\n"; usage(2); }
  } else if (a.extend.empty() || a.nano.empty() || a.out.empty()) {
    std::cerr << "ERROR: provide either --match, or both --extend file and --nano, "
                 "plus --out\n";
    usage(2);
  }
  if (a.label.empty()) {
    std::string b = a.out;
    auto slash = b.find_last_of('/');
    if (slash != std::string::npos) b = b.substr(slash + 1);
    auto dot = b.find_last_of('.');
    if (dot != std::string::npos) b = b.substr(0, dot);
    a.label = b;
  }
  return a;
}

TH1* getHist(const std::string& file, const char* name) {
  TFile* f = TFile::Open(file.c_str());
  if (!f || f->IsZombie()) {
    std::cerr << "ERROR: cannot open " << file << "\n"; std::exit(3);
  }
  TH1* h = dynamic_cast<TH1*>(f->Get(name));
  if (!h) {
    // Back-compat: files written before the 2026-07 rename carry the old
    // "h_sidecar_*" histogram names.  If the requested "h_extend_*" name is
    // absent, retry with the legacy "h_sidecar_*" spelling before failing.
    std::string nm(name);
    const std::string pfxNew = "h_extend_", pfxOld = "h_sidecar_";
    if (nm.rfind(pfxNew, 0) == 0) {
      std::string legacy = pfxOld + nm.substr(pfxNew.size());
      h = dynamic_cast<TH1*>(f->Get(legacy.c_str()));
      if (h) std::cerr << "[plotTtbarCompare] note: using legacy histogram name '"
                       << legacy << "' (pre-rename file)\n";
    }
  }
  if (!h) {
    std::cerr << "ERROR: histogram '" << name << "' not found in " << file << "\n";
    std::exit(4);
  }
  h->SetDirectory(nullptr);   // detach so we can close the file safely
  f->Close();
  return h;
}

}  // namespace

int main(int argc, char** argv) {
  const Args args = parseArgs(argc, argv);

  const bool matchMode = !args.match.empty();

  std::cout << "[plotTtbarCompare] starting\n";
  if (matchMode) {
    std::cout << "[plotTtbarCompare]   match     = " << args.match << "\n";
  } else {
    std::cout << "[plotTtbarCompare]   extend file   = " << args.extend << "\n";
    std::cout << "[plotTtbarCompare]   nano      = " << args.nano << "\n";
  }
  std::cout << "[plotTtbarCompare]   out       = " << args.out << "\n";
  std::cout << "[plotTtbarCompare]   normalize = " << (args.normalize ? "yes" : "no") << "\n";

  TH1 *hNano = nullptr, *hSide = nullptr, *hTtbb = nullptr;
  if (matchMode) {
    // Single match file (from matchTtbarId --out): all three histograms,
    // filled over matched events only.
    hNano = getHist(args.match, "h_genTtbarId_sub");
    hSide = getHist(args.match, "h_extend_genTtbarId_sub");
    hTtbb = getHist(args.match, "h_extend_Expanded_sub");
  } else {
    // Separate hist files from makeTtbarHist.
    hNano = getHist(args.nano,    "h_genTtbarId_sub");
    hSide = getHist(args.extend, "h_genTtbarId_sub");
    hTtbb = getHist(args.extend, "h_Expanded_sub");
  }

  if (args.normalize) {
    if (hNano->Integral() > 0) hNano->Scale(1.0 / hNano->Integral());
    if (hSide->Integral() > 0) hSide->Scale(1.0 / hSide->Integral());
    if (hTtbb->Integral() > 0) hTtbb->Scale(1.0 / hTtbb->Integral());
  }

  gStyle->SetOptStat(0);

  TCanvas c("c", "ttbarId comparison", 900, 600);
  if (args.logy) c.SetLogy();

  // nano: filled bars
  hNano->SetTitle((args.label + " : genTtbarId sub-code (nano vs extend file)").c_str());
  hNano->SetFillColorAlpha(kAzure - 9, 0.6);
  hNano->SetLineColor(kAzure + 2);
  hNano->SetLineWidth(1);
  hNano->GetYaxis()->SetTitle(args.normalize ? "fraction" : "events");
  hNano->GetXaxis()->SetTitle("genTtbarId % 100");
  // headroom for the ratio labels above the tallest bar
  {
    double ymax = hNano->GetMaximum();
    if (hSide->GetMaximum() > ymax) ymax = hSide->GetMaximum();
    if (!args.logy) hNano->SetMaximum(ymax * 1.25);
  }
  hNano->Draw("HIST");

  // extend file genTtbarId: points (should sit exactly on nano)
  hSide->SetMarkerStyle(20);
  hSide->SetMarkerSize(0.8);
  hSide->SetMarkerColor(kBlack);
  hSide->SetLineColor(kBlack);
  hSide->Draw("E1 SAME");

  // extend file Expanded_genTtbarId: open red points (shows 61/62/71/72 appearing)
  hTtbb->SetMarkerStyle(24);
  hTtbb->SetMarkerSize(0.8);
  hTtbb->SetMarkerColor(kRed + 1);
  hTtbb->SetLineColor(kRed + 1);
  hTtbb->Draw("E1 SAME");

  TLegend leg(0.55, 0.72, 0.88, 0.88);
  leg.SetBorderSize(0);
  leg.SetFillStyle(0);
  leg.AddEntry(hNano, "nano genTtbarId", "f");
  leg.AddEntry(hSide, "extend file genTtbarId", "pe");
  leg.AddEntry(hTtbb, "extend file Expanded_genTtbarId", "pe");
  leg.Draw();

  // ---- per-bin ratio (extend file genTtbarId / nano) drawn as text above each bar ----
  // The ratio is ~1.0 everywhere, so a separate panel adds little; instead we
  // print the number over each populated bin.  Red if it deviates from 1.
  TLatex tl;
  tl.SetTextSize(0.022);
  tl.SetTextAlign(21);             // centered horizontally, bottom vertically
  tl.SetTextAngle(90);            // vertical text so adjacent bins don't overlap
  for (int b = 1; b <= hNano->GetNbinsX(); ++b) {
    const double cN = hNano->GetBinContent(b);
    const double cS = hSide->GetBinContent(b);
    if (cN == 0 && cS == 0) continue;
    double r = (cN > 0) ? cS / cN : 0.0;
    char txt[32];
    if (cN > 0) std::snprintf(txt, sizeof(txt), "%.3f", r);
    else        std::snprintf(txt, sizeof(txt), "N/A");
    const bool bad = (cN > 0) && (std::fabs(r - 1.0) > 1e-6);
    tl.SetTextColor(bad ? (kRed + 1) : kGray + 2);
    const double x = hNano->GetBinCenter(b);
    const double y = std::max(cN, cS);
    tl.DrawLatex(x, y + (args.logy ? y * 0.15 : hNano->GetMaximum() * 0.02), txt);
  }

  c.SaveAs(args.out.c_str());
  std::cout << "[plotTtbarCompare] wrote " << args.out << "\n";

  // build a ratio histogram only for the text summary below
  TH1* hRatio = static_cast<TH1*>(hSide->Clone("h_ratio"));
  hRatio->SetDirectory(nullptr);
  hRatio->Divide(hNano);

  // ---- text summary: where does extend file/nano deviate from 1? ----
  std::cout << "[plotTtbarCompare] ratio check (extend file genTtbarId / nano genTtbarId):\n";
  int nBad = 0;
  for (int b = 1; b <= hRatio->GetNbinsX(); ++b) {
    const double nN = hNano->GetBinContent(b);
    const double nS = hSide->GetBinContent(b);
    if (nN == 0 && nS == 0) continue;
    const double r = hRatio->GetBinContent(b);
    const int sub = static_cast<int>(hRatio->GetBinLowEdge(b));
    if (nN == 0 || std::abs(r - 1.0) > 1e-9) {
      std::cout << "    sub-code " << sub
                << " : nano=" << nN << " extend file=" << nS
                << " ratio=" << r << "\n";
      ++nBad;
    }
  }
  if (nBad == 0)
    std::cout << "    >>> every populated sub-code has ratio == 1.0 "
                 "(extend file genTtbarId reproduces nano exactly).\n";
  else
    std::cout << "    >>> " << nBad << " sub-code(s) differ; see lines above. "
                 "(Differences are EXPECTED only if event sets differ; "
                 "use --normalize for a shape-only check.)\n";

  return 0;
}
