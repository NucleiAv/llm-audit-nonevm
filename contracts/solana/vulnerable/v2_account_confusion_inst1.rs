// V2: Account confusion (type confusion) - Instance 1
// Based on: Cashio exploit, March 2022. ~$52M loss.
// Source: Halborn post-mortem, CertiK incident analysis.
// Vulnerability: The mint instruction accepts collateral_mint as a raw
// AccountInfo without verifying its owner or mint key against a trusted
// registry. An attacker can pass a worthless SPL mint they control in place
// of the expected USDC/USDT collateral mint, minting CASH against zero value.

use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount};

declare_id!("CASH1111111111111111111111111111111111111111");

#[program]
pub mod cashio {
    use super::*;

    pub fn initialize(
        ctx: Context<Initialize>,
        treasury_mint: Pubkey,
        bump: u8,
    ) -> Result<()> {
        let state = &mut ctx.accounts.state;
        state.treasury_mint = treasury_mint;
        state.total_supply = 0;
        state.bump = bump;
        Ok(())
    }

    // BUG: collateral_mint is AccountInfo — no check that it equals
    // state.treasury_mint or that its owner is the SPL Token program.
    // Any mint the attacker creates passes through.
    pub fn mint_cash(ctx: Context<MintCash>, collateral_amount: u64) -> Result<()> {
        // Pretend 1:1 collateral ratio — no actual verification of what mint was passed.
        let state = &mut ctx.accounts.state;
        state.total_supply = state.total_supply.wrapping_add(collateral_amount);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + State::SIZE,
        seeds = [b"state"],
        bump
    )]
    pub state: Account<'info, State>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct MintCash<'info> {
    #[account(mut, seeds = [b"state"], bump = state.bump)]
    pub state: Account<'info, State>,
    pub user: Signer<'info>,
    // BUG: raw AccountInfo — owner, mint key, and program ownership unchecked.
    pub collateral_mint: AccountInfo<'info>,
    #[account(mut)]
    pub user_collateral_account: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[account]
pub struct State {
    pub treasury_mint: Pubkey,
    pub total_supply: u64,
    pub bump: u8,
}

impl State {
    pub const SIZE: usize = 32 + 8 + 1;
}
