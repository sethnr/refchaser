from ingest.ingest_paper import ingest_paper
from context.build_context_for_references import build_context_for_references
from output.write_output import write_output


def run(pdf_path):
    print("Ingesting paper...")
    main_text, references, style = ingest_paper(pdf_path)

    print(f"{len(references)} references extracted")

    # print("First five references:")
    # for ref in references[:5]:
    #     print(ref)
    # print("Last five references:")
    # for ref in references[-5:]:
    #     print(ref)


    print("Citation style:", style)

    print("Building context...")
    results, total_cost = build_context_for_references(main_text, references, style)

    print("Writing output...")
    prefix = pdf_path.replace(".pdf", "")
    write_output(results, prefix=prefix)

    print("Done.")
    print(f"Total cost: ${total_cost:.4f}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python run_paper_context.py paper.pdf")
        sys.exit(1)

    run(sys.argv[1])