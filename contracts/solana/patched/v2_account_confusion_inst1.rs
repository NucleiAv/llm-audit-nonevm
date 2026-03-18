// V2: Account confusion - Instance 1 (PATCHED)
// Fix: collateral_mint is typed as Account<'info, Mint> and constrained
// with address = state.treasury_mint so only the registered mint is accepted.

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

    pub fn mint_cash(ctx: Context<MintCash>, collateral_amount: u64) -> Result<()> {
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
    // FIX: typed as Mint and constrained to the registered treasury_mint address.
    #[account(address = state.treasury_mint)]
    pub collateral_mint: Account<'info, Mint>,
    #[account(mut, token::mint = collateral_mint)]
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
