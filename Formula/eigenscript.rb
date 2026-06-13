class Eigenscript < Formula
  desc "Bytecode VM language with copy-and-patch JIT, observers, and temporal queries"
  homepage "https://github.com/InauguralSystems/EigenScript"
  url "https://github.com/InauguralSystems/EigenScript/archive/refs/tags/v0.13.0.tar.gz"
  sha256 "fe32cc505417da0a876dc671f899bd8dd2e11e608a6950dafb6d93d206a498ce"
  license "MIT"
  head "https://github.com/InauguralSystems/EigenScript.git", branch: "main"

  uses_from_macos "zlib"

  def install
    # v0.13.0's Makefile has unconditional `-Wl,-z,relro,-z,now` in LDFLAGS,
    # which is GNU-ld-only. The Linux-gating fix is in main but landed after
    # the tag — patch the released Makefile here. Once the next tagged
    # release ships with the gating, this inreplace will stop matching and
    # the formula will fail loudly, prompting the bump.
    if OS.mac?
      inreplace "Makefile",
                "LDFLAGS := -pie -Wl,-z,relro,-z,now -lm -lpthread",
                "LDFLAGS := -lm -lpthread"
    end

    system "make", "install", "PREFIX=#{prefix}", "CC=#{ENV.cc}"
  end

  test do
    (testpath/"hello.eigs").write <<~EIGS
      print of "hello"
    EIGS
    assert_equal "hello\n", shell_output("#{bin}/eigenscript #{testpath}/hello.eigs")

    # Confirms the runtime found its stdlib at prefix/lib/eigenscript/.
    (testpath/"stdlib.eigs").write <<~EIGS
      import calculus
      print of "stdlib-ok"
    EIGS
    assert_equal "stdlib-ok\n", shell_output("#{bin}/eigenscript #{testpath}/stdlib.eigs")
  end
end
