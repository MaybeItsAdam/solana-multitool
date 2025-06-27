package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"

	solanaswapgo "github.com/MaybeItsAdam/solanaswap-go/solanaswap-go"
	solana "github.com/gagliardetto/solana-go"
	"github.com/gagliardetto/solana-go/rpc"
	"github.com/joho/godotenv"
)

func main() {
	// Load .env from config directory at project root (two directories up from this file)
	_ = godotenv.Load("../config/.env")

	// Get QuickNode URL from environment variable
	solanaRPCURL := os.Getenv("SOLANA_RPC_URL")
	if solanaRPCURL == "" {
		log.Fatal("QUICKNODE_URL not set in environment or .env file")
	}

	// Set up RPC client with QuickNode endpoint
	rpcClient := rpc.New(solanaRPCURL)

	sig := os.Args[1]

	// Replace with your actual transaction signature
	txSig := solana.MustSignatureFromBase58(sig)

	// Specify the maximum transaction version supported
	var maxTxVersion uint64 = 0

	// Fetch the transaction data using the RPC client
	tx, err := rpcClient.GetTransaction(
		context.Background(),
		txSig,
		&rpc.GetTransactionOpts{
			Commitment:                     rpc.CommitmentConfirmed,
			MaxSupportedTransactionVersion: &maxTxVersion,
		},
	)
	if err != nil {
		log.Fatalf("Error fetching transaction: %s", err)
	}

	// Initialize the transaction parser using solanaswapgo
	parser, err := solanaswapgo.NewTransactionParser(tx)
	if err != nil {
		log.Fatalf("Error initializing transaction parser: %s", err)
	}

	// Parse the transaction to extract basic data
	transactionData, err := parser.ParseTransaction()
	if err != nil {
		log.Fatalf("Error parsing transaction: %s", err)
	}

	// Process and extract swap-specific data from the parsed transaction
	swapData, err := parser.ProcessSwapData(transactionData)
	if err != nil {
		log.Fatalf("Error processing swap data: %s", err)
	}

	// Combine both outputs into a single JSON object
	combined := map[string]any{
		"swap_data":        swapData,
		"transaction_data": transactionData,
	}

	marshalledCombined, _ := json.MarshalIndent(combined, "", "  ")
	fmt.Println(string(marshalledCombined))
}
